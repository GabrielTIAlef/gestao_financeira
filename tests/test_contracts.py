from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from examples.synthetic import frames, write_workbook
from src.config import ETLError, ROOT, database_url, input_path
from src.contracts import convert, read_workbook, totals, validate


class ContractTests(unittest.TestCase):
    def test_valid_sample_and_exact_totals(self):
        clean = validate(frames())
        self.assertEqual(totals(clean)['Faturamento']['Receita_Bruta'], '170.00')
        self.assertEqual(totals(clean)['Custos_Despesas']['Valor'], '35.30')
        self.assertEqual(clean['Faturamento'].iloc[0]['Data_Competencia'], date(2026, 1, 1))

    def test_dates_reject_invalid_ambiguous_serial_and_time(self):
        for value in ('2026-02-30', '01/02/2026', 46000, '', None,
                      datetime(2026, 1, 1, 1), True):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(ValueError):
                convert(value, 'date')

    def test_excel_midnight_date_accepted(self):
        self.assertEqual(convert(datetime(2026, 1, 1), 'date'), date(2026, 1, 1))

    def test_decimal_precision_and_nonfinite_rejected(self):
        for value in ('1.001', 'Infinity', float('nan'), True, '1.000,00', '10000000000000000'):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(ValueError):
                convert(value, 'money')

    def test_signed_money_and_decimal_sum(self):
        self.assertEqual(convert('-0.10', 'money'), Decimal('-0.10'))
        self.assertEqual(convert(0.1, 'money') + convert(0.2, 'money'), Decimal('0.30'))

    def test_ratio_not_percent_text_or_excess_precision(self):
        for value in ('25%', '0.12345'):
            with self.assertRaises(ValueError):
                convert(value, 'ratio')

    def test_days_nonnegative_integer(self):
        for value in (-1, 1.5, True, '2147483648'):
            with self.assertRaises(ValueError):
                convert(value, 'integer')

    def test_identifiers_preserve_zeroes_and_case(self):
        self.assertEqual(convert(' 00Ab01 ', 'id'), '00Ab01')
        with self.assertRaises(ValueError):
            convert(123, 'id')

    def test_names_normalize_but_do_not_strip_accents(self):
        self.assertEqual(convert('  UNIDADE   Á ', 'name'), 'unidade á')
        self.assertNotEqual(convert('á', 'name'), convert('a', 'name'))

    def test_controls_and_empty_names_rejected(self):
        for value in ('  ', 'a\nb', 'x' * 201):
            with self.assertRaises(ValueError):
                convert(value, 'name')

    def test_all_five_sheets_required_and_no_extra(self):
        for change in ('missing', 'extra'):
            sample = frames()
            if change == 'missing':
                sample.pop('Metas_Negocio')
            else:
                sample['Auxiliar'] = pd.DataFrame({'x': [1]})
            with self.assertRaises(ETLError):
                validate(sample)

    def test_duplicate_business_ids_rejected(self):
        for sheet, key in (('Faturamento', 'ID_Lancamento'), ('Custos_Despesas', 'ID_Lancamento'),
                           ('Contas_Receber', 'ID_Titulo')):
            sample = frames()
            sample[sheet].loc[1, key] = sample[sheet].loc[0, key]
            with self.subTest(sheet=sheet), self.assertRaises(ETLError):
                validate(sample)

    def test_duplicate_budget_and_targets_rejected_after_normalization(self):
        for sheet in ('Orcamento', 'Metas_Negocio'):
            sample = frames()
            sample[sheet].loc[1, 'Unidade_Negocio'] = ' UNIDADE A '
            with self.assertRaises(ETLError):
                validate(sample)

    def test_different_period_targets_preserved(self):
        sample = frames()
        sample['Metas_Negocio'].loc[1, ['Unidade_Negocio', 'Data_Competencia']] = ['Unidade A', '2026-02-01']
        self.assertEqual(len(validate(sample)['Metas_Negocio']), 2)

    def test_missing_extra_and_duplicate_columns_rejected(self):
        for mode in ('missing', 'extra', 'duplicate'):
            sample = frames()
            frame = sample['Faturamento']
            if mode == 'missing':
                sample['Faturamento'] = frame.drop(columns='ID_Lancamento')
            elif mode == 'extra':
                frame['Extra'] = 'x'
            else:
                frame.columns = list(frame.columns[:-1]) + ['Impostos']
            with self.assertRaises(ETLError):
                validate(sample)

    def test_legacy_budget_category_requires_explicit_adaptation(self):
        sample = frames()
        sample['Orcamento'] = sample['Orcamento'].rename(columns={'Unidade_Negocio': 'Categoria'})
        with self.assertRaises(ETLError):
            validate(sample)

    def test_empty_lot_rejected(self):
        sample = frames()
        sample['Orcamento'] = sample['Orcamento'].iloc[:0]
        with self.assertRaises(ETLError):
            validate(sample)

    def test_null_key_and_value_rejected(self):
        for column in ('Cliente', 'Data_Competencia', 'Receita_Bruta'):
            sample = frames()
            sample['Faturamento'].loc[0, column] = None
            with self.assertRaises(ETLError):
                validate(sample)

    def test_financial_equation_rejected_without_disclosing_value(self):
        sample = frames()
        sample['Faturamento'].loc[0, 'Receita_Liquida'] = '999999.99'
        with self.assertRaises(ETLError) as raised:
            validate(sample)
        self.assertNotIn('999999.99', str(raised.exception))

    def test_target_domain_rejected(self):
        for column, value in (('Margem_Meta', '1.1'), ('Crescimento_Meta', '-1.1'), ('Ticket_Medio_Meta', '-1')):
            sample = frames()
            sample['Metas_Negocio'].loc[0, column] = value
            with self.assertRaises(ETLError):
                validate(sample)

    def test_excel_roundtrip_hash_and_text_id(self):
        with tempfile.TemporaryDirectory() as temp:
            sample = frames()
            sample['Faturamento'].loc[0, 'ID_Lancamento'] = '0001'
            path = write_workbook(Path(temp) / 'sample.xlsx', sample)
            clean, digest = read_workbook(path)
            self.assertEqual(clean['Faturamento'].loc[0, 'ID_Lancamento'], '0001')
            self.assertEqual(digest, sha256(path.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                write_workbook(path)

    def test_bad_file_is_safe_error(self):
        for path in ('not_present.xlsx', 'not_present.csv'):
            with self.assertRaises(ETLError):
                read_workbook(path)


class ConfigurationTests(unittest.TestCase):
    def test_demo_rejects_external_hosts_and_query_redirection_before_engine(self):
        from scripts.run_demo import main
        for value in ('postgresql+psycopg2://finance_test@example.invalid/finance_demo',
                      'postgresql+psycopg2://finance_test@127.0.0.1/finance_demo?host=example.invalid',
                      'postgresql+psycopg2://finance_test@127.0.0.1/producao'):
            with patch.dict(os.environ, {'FINANCE_DEMO_DATABASE_URL': value}, clear=True), \
                    patch('scripts.run_demo.create_engine', side_effect=AssertionError('conexão')), \
                    patch('sys.stderr'):
                self.assertEqual(main(), 1)

    @patch('src.config.load_dotenv')
    def test_missing_config_fails_without_defaults(self, _):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ETLError):
            database_url()

    @patch('src.config.load_dotenv')
    def test_password_special_characters_encoded_by_library(self, _):
        env = {'POSTGRES_HOST': 'localhost', 'POSTGRES_DB': 'ficticio',
               'POSTGRES_USER': 'finance_app', 'POSTGRES_PASSWORD': 'ficticio:@/#%'}
        with patch.dict(os.environ, env, clear=True):
            url = database_url()
        self.assertEqual(url.password, env['POSTGRES_PASSWORD'])
        self.assertNotIn(env['POSTGRES_PASSWORD'], str(url))

    @patch('src.config.load_dotenv')
    def test_invalid_port_rejected(self, _):
        env = {'POSTGRES_HOST': 'localhost', 'POSTGRES_DB': 'ficticio',
               'POSTGRES_USER': 'finance_app', 'POSTGRES_PASSWORD': 'ficticio', 'POSTGRES_PORT': '0'}
        with patch.dict(os.environ, env, clear=True), self.assertRaises(ETLError):
            database_url()

    @patch('src.config.load_dotenv')
    def test_relative_path_resolves_from_repository(self, _):
        self.assertEqual(input_path('data/demo.xlsx'), ROOT / 'data/demo.xlsx')

    @patch('src.config.load_dotenv')
    def test_input_required(self, _):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ETLError):
            input_path()

    def test_import_has_no_io_or_connection(self):
        import src.ETL as etl
        with patch('pandas.ExcelFile', side_effect=AssertionError('I/O')), \
                patch('sqlalchemy.create_engine', side_effect=AssertionError('conexão')):
            importlib.reload(etl)

    def test_cli_suppresses_unexpected_error_details(self):
        import src.ETL as etl
        with patch('sys.argv', ['ETL.py', '--init']), patch('src.ETL.database_url',
                side_effect=RuntimeError('sentinela-ficticia')), self.assertLogs(level='ERROR') as logs:
            self.assertEqual(etl.main(), 1)
        self.assertNotIn('sentinela-ficticia', '\n'.join(logs.output))


if __name__ == '__main__':
    unittest.main()
