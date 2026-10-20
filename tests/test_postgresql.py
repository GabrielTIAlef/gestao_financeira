"""Integração exclusiva em bancos descartáveis de um cluster local autorizado."""
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from examples.synthetic import frames, write_workbook
from src.ETL import run
from src.config import ETLError, ROOT
from src.contracts import validate
from src.model import FACTS
from src import warehouse

ADMIN_URL = os.getenv('FINANCE_TEST_PG_ADMIN_URL')
ISOLATED = os.getenv('FINANCE_TEST_PG_ISOLATED') == '1'


@unittest.skipUnless(ADMIN_URL and ISOLATED, 'PostgreSQL isolado não iniciado; use scripts/validate_postgres.py')
class PostgreSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = make_url(ADMIN_URL)
        if (url.drivername != 'postgresql+psycopg2' or url.query
                or url.host not in ('localhost', '127.0.0.1', '::1')
                or url.database != 'postgres' or url.username != 'finance_test'):
            raise RuntimeError('Testes exigem cluster local explícito com usuário finance_test.')
        cls.url = url
        cls.admin = create_engine(url, poolclass=NullPool, isolation_level='AUTOCOMMIT',
                                  connect_args={'connect_timeout': 10})

    @classmethod
    def tearDownClass(cls):
        cls.admin.dispose()

    def setUp(self):
        self.name = 'finance_test_' + uuid.uuid4().hex
        with self.admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{self.name}"'))
        self.engine = create_engine(self.url.set(database=self.name), connect_args={'connect_timeout': 10})
        self.directory = tempfile.TemporaryDirectory(prefix='finance_pg_test_')
        warehouse.initialize(self.engine)

    def tearDown(self):
        self.engine.dispose()
        assert self.name.startswith('finance_test_') and len(self.name) == 45
        with self.admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE "{self.name}" WITH (FORCE)'))
        temp = Path(self.directory.name).resolve()
        assert temp.parent == Path(tempfile.gettempdir()).resolve() and temp.name.startswith('finance_pg_test_')
        self.directory.cleanup()

    def scalar(self, sql):
        with self.engine.connect() as conn:
            return conn.execute(text(sql)).scalar_one()

    def execute(self, sql):
        with self.engine.begin() as conn:
            conn.execute(text(sql))

    def load(self, source=None):
        return warehouse.publish(self.engine, frames() if source is None else source, 'a' * 64)

    def snapshot(self):
        tables = [f'dw.{s["table"]}' for s in FACTS.values()] + ['dw.etl_batch']
        tables += [f'stg."{sheet}"' for sheet in FACTS]
        with self.engine.connect() as conn:
            return {table: conn.execute(text(f'SELECT * FROM {table} ORDER BY 1')).all() for table in tables}

    def test_schema_has_nine_dimensions_five_facts_and_constraints(self):
        tables = inspect(self.engine).get_table_names(schema='dw')
        self.assertEqual(sum(n.startswith('dim_') for n in tables), 9)
        self.assertEqual(sum(n.startswith('fato_') for n in tables), 5)
        self.assertEqual(len(inspect(self.engine).get_view_names(schema='dw')), 3)
        for spec in FACTS.values():
            unique = inspect(self.engine).get_unique_constraints(spec['table'], schema='dw')
            self.assertIn(set(spec['keys']), [set(c['column_names']) for c in unique])
            self.assertTrue(inspect(self.engine).get_foreign_keys(spec['table'], schema='dw'))

    def test_distinct_launches_at_same_dimensions_are_not_discarded(self):
        self.load()
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.fato_faturamento'), 3)
        self.assertEqual(self.scalar('SELECT SUM(receita_bruta) FROM dw.fato_faturamento'), Decimal('170.00'))
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.fato_custos_despesas'), 3)
        self.assertEqual(self.scalar('SELECT SUM(valor) FROM dw.fato_custos_despesas'), Decimal('35.30'))

    def test_identical_titles_with_distinct_ids_are_preserved(self):
        self.load()
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.fato_contas_receber'), 2)
        self.assertEqual(self.scalar('SELECT sum(valor) FROM dw.fato_contas_receber'), Decimal('200.20'))

    def test_repeat_has_no_business_duplication_and_keeps_dimension_ids(self):
        first = self.load()
        with self.engine.connect() as conn:
            dimensions = conn.execute(text('SELECT * FROM dw.dim_cliente ORDER BY cliente_id')).all()
        second = self.load()
        self.assertNotEqual(first['batch_id'], second['batch_id'])
        for sheet, spec in FACTS.items():
            self.assertEqual(self.scalar(f'SELECT count(*) FROM dw.{spec["table"]}'), len(frames()[sheet]))
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.etl_batch'), 2)
        with self.engine.connect() as conn:
            self.assertEqual(dimensions, conn.execute(text('SELECT * FROM dw.dim_cliente ORDER BY cliente_id')).all())

    def test_receivable_update_changes_value_status_days_without_new_title(self):
        self.load()
        before_id = self.scalar("SELECT row_id FROM dw.fato_contas_receber WHERE id_titulo='T001'")
        sample = frames()
        sample['Contas_Receber'].loc[0, ['Valor', 'Status', 'Dias_Atraso', 'Data_Vencimento']] = [
            '80.25', 'Vencido', 12, '2026-02-01']
        self.load(sample)
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.fato_contas_receber'), 2)
        self.assertEqual(self.scalar("SELECT valor FROM dw.fato_contas_receber WHERE id_titulo='T001'"), Decimal('80.25'))
        self.assertEqual(self.scalar("SELECT dias_atraso FROM dw.fato_contas_receber WHERE id_titulo='T001'"), 12)
        self.assertEqual(self.scalar("SELECT row_id FROM dw.fato_contas_receber WHERE id_titulo='T001'"), before_id)
        self.assertEqual(self.scalar("SELECT s.status FROM dw.fato_contas_receber f JOIN dw.dim_status s USING(status_id) WHERE id_titulo='T001'"), 'vencido')

    def test_revenue_correction_replaces_values_and_dimension_reference(self):
        self.load()
        sample = frames()
        sample['Faturamento'].loc[0, ['Receita_Bruta', 'Impostos', 'Receita_Liquida', 'Unidade_Negocio']] = [
            '200.00', '20.00', '180.00', 'Unidade Corrigida']
        self.load(sample)
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.fato_faturamento'), 3)
        self.assertEqual(self.scalar('SELECT sum(receita_bruta) FROM dw.fato_faturamento'), Decimal('269.90'))
        self.assertEqual(self.scalar("SELECT u.unidade_negocio FROM dw.fato_faturamento f JOIN dw.dim_unidade_negocio u USING(unidade_negocio_id) WHERE id_lancamento='F001'"), 'unidade corrigida')

    def test_cost_and_budget_corrections_update_existing_keys(self):
        self.load()
        sample = frames()
        sample['Custos_Despesas'].loc[0, 'Valor'] = '12.34'
        sample['Orcamento'].loc[0, 'Valor_Orcado'] = '300.00'
        self.load(sample)
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.fato_orcamento'), 2)
        self.assertEqual(self.scalar('SELECT sum(valor_orcado) FROM dw.fato_orcamento'), Decimal('350.00'))
        self.assertEqual(self.scalar("SELECT valor FROM dw.fato_custos_despesas WHERE id_lancamento='C001'"), Decimal('12.34'))

    def test_targets_keep_separate_periods_and_new_unit_is_loaded(self):
        self.load()
        sample = frames()
        sample['Metas_Negocio'].loc[0, 'Data_Competencia'] = '2026-02-01'
        sample['Metas_Negocio'].loc[1, 'Unidade_Negocio'] = 'Unidade Só Metas'
        self.load(sample)
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.fato_metas_negocio'), 4)
        self.assertEqual(self.scalar("SELECT count(*) FROM dw.dim_unidade_negocio WHERE unidade_negocio='unidade só metas'"), 1)

    def test_absent_source_key_does_not_delete_previous_fact(self):
        self.load()
        sample = frames()
        sample['Faturamento'] = sample['Faturamento'].iloc[:1]
        self.load(sample)
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.fato_faturamento'), 3)
        self.assertEqual(self.scalar('SELECT count(*) FROM stg."Faturamento"'), 1)

    def test_invalid_input_preserves_previous_staging_facts_and_batch(self):
        self.load()
        before = self.snapshot()
        sample = frames()
        sample['Contas_Receber'].loc[0, 'Data_Emissao'] = 'inválida'
        with self.assertRaises(ETLError):
            self.load(sample)
        self.assertEqual(before, self.snapshot())

    def test_staging_failure_rolls_back_all_previous_writes(self):
        self.load()
        self.execute('ALTER TABLE stg."Custos_Despesas" ADD COLUMN obrigatorio text NOT NULL DEFAULT \'x\'')
        self.execute('ALTER TABLE stg."Custos_Despesas" ALTER COLUMN obrigatorio DROP DEFAULT')
        before = self.snapshot()
        with self.assertRaises(ETLError):
            self.load()
        self.assertEqual(before, self.snapshot())

    def test_sql_failure_after_revenue_update_rolls_back_all_tables(self):
        self.load()
        self.execute("CREATE FUNCTION dw.reject_cost() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'falha ficticia'; END $$")
        self.execute('CREATE TRIGGER reject_cost BEFORE INSERT OR UPDATE ON dw.fato_custos_despesas FOR EACH ROW EXECUTE FUNCTION dw.reject_cost()')
        before = self.snapshot()
        sample = frames()
        sample['Faturamento'].loc[0, ['Receita_Bruta', 'Impostos', 'Receita_Liquida']] = ['200', '20', '180']
        with self.assertRaises(ETLError) as raised:
            self.load(sample)
        self.assertNotIn('falha ficticia', str(raised.exception))
        self.assertEqual(before, self.snapshot())
        self.execute('DROP TRIGGER reject_cost ON dw.fato_custos_despesas')
        self.load(sample)  # Lock também deve ter sido liberado após a falha.

    def test_missing_dimension_join_is_detected_and_rolled_back(self):
        with patch('src.warehouse._dimensions', return_value=None), self.assertRaises(ETLError):
            self.load()
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.etl_batch'), 0)
        self.assertEqual(self.scalar('SELECT count(*) FROM stg."Faturamento"'), 0)

    def test_monetary_reconciliation_failure_rolls_back_dimensions_and_facts(self):
        original = warehouse._fact_sql
        def wrong_value(sheet, spec):
            sql = original(sheet, spec)
            return sql.replace('s."Valor"', '(s."Valor" + 1)') if sheet == 'Custos_Despesas' else sql
        with patch('src.warehouse._fact_sql', side_effect=wrong_value), self.assertRaises(ETLError):
            self.load()
        for table in ('dw.etl_batch', 'dw.dim_cliente', 'dw.fato_faturamento', 'stg."Faturamento"'):
            self.assertEqual(self.scalar(f'SELECT count(*) FROM {table}'), 0)

    def test_concurrent_load_rejected_then_lock_released(self):
        with self.engine.connect() as other:
            other.execute(text('SELECT pg_advisory_lock(:key)'), {'key': warehouse.LOCK_ID})
            try:
                with self.assertRaisesRegex(ETLError, 'Outra carga'):
                    self.load()
            finally:
                other.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': warehouse.LOCK_ID})
        self.load()

    def test_initialize_is_repeatable_and_preserves_data(self):
        self.load()
        before = self.snapshot()
        warehouse.initialize(self.engine)
        self.assertEqual(before, self.snapshot())

    def test_schema_version_mismatch_rejected_without_writes(self):
        self.load()
        self.execute("UPDATE dw.schema_version SET ddl_sha256 = repeat('0', 64)")
        before = self.snapshot()
        with self.assertRaises(ETLError):
            self.load()
        self.assertEqual(before, self.snapshot())

    def test_missing_schema_marker_rejected(self):
        self.execute('DROP TABLE dw.schema_version')
        with self.assertRaises(ETLError):
            self.load()
        self.assertEqual(self.scalar('SELECT count(*) FROM dw.etl_batch'), 0)

    def test_legacy_objects_are_not_migrated_or_overwritten(self):
        name = 'finance_test_' + uuid.uuid4().hex
        with self.admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        engine = create_engine(self.url.set(database=name))
        try:
            with engine.begin() as conn:
                conn.execute(text('CREATE SCHEMA stg'))
                conn.execute(text('CREATE TABLE stg.legado(valor integer)'))
                conn.execute(text('INSERT INTO stg.legado VALUES (42)'))
            with self.assertRaises(ETLError):
                warehouse.initialize(engine)
            with engine.connect() as conn:
                self.assertEqual(conn.execute(text('SELECT valor FROM stg.legado')).scalar_one(), 42)
                self.assertFalse(inspect(conn).has_table('schema_version', schema='dw'))
        finally:
            engine.dispose()
            assert name.startswith('finance_test_') and len(name) == 45
            with self.admin.connect() as conn:
                conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))

    def test_foreign_keys_and_business_uniqueness_enforced_by_database(self):
        self.load()
        for sql in ("UPDATE dw.fato_faturamento SET cliente_id=-1 WHERE id_lancamento='F001'",
                    "UPDATE dw.fato_faturamento SET id_lancamento='F001' WHERE id_lancamento='F002'",
                    "UPDATE dw.fato_contas_receber SET valor=NULL WHERE id_titulo='T001'",
                    "UPDATE dw.fato_faturamento SET receita_liquida=0 WHERE id_lancamento='F001'"):
            with self.subTest(sql_kind=sql.split()[0]), self.assertRaises(Exception):
                self.execute(sql)
        self.assertEqual(self.scalar('SELECT sum(receita_liquida) FROM dw.fato_faturamento'), Decimal('153.00'))

    def test_numeric_database_types_preserve_cents_and_views(self):
        self.load()
        columns = {c['name']: c['type'] for c in inspect(self.engine).get_columns('fato_faturamento', schema='dw')}
        self.assertEqual((columns['receita_bruta'].precision, columns['receita_bruta'].scale), (18, 2))
        self.assertEqual(self.scalar("SELECT receita_bruta FROM dw.vw_faturamento_mensal WHERE unidade_negocio='unidade a'"), Decimal('150.00'))
        self.assertEqual(self.scalar('SELECT sum(valor) FROM dw.vw_custos_mensais'), Decimal('35.30'))

    def test_external_view_survives_repeated_load(self):
        self.load()
        self.execute('CREATE VIEW public.external_report AS SELECT sum(receita_bruta) AS total FROM dw.fato_faturamento')
        oid = self.scalar("SELECT 'public.external_report'::regclass::oid")
        self.load()
        self.assertEqual(self.scalar("SELECT 'public.external_report'::regclass::oid"), oid)
        self.assertEqual(self.scalar('SELECT total FROM public.external_report'), Decimal('170.00'))

    def test_batch_ledger_keeps_source_counts_and_totals(self):
        result = self.load()
        with self.engine.connect() as conn:
            row = conn.execute(text('SELECT * FROM dw.etl_batch')).mappings().one()
        self.assertEqual(row['source_counts']['Faturamento'], 3)
        self.assertEqual(row['source_totals']['Faturamento']['Receita_Bruta'], '170.00')
        self.assertEqual(str(row['batch_id']), result['batch_id'])
        self.assertIsNotNone(row['tempo_carga'].tzinfo)

    def test_excel_to_postgresql_uses_all_five_sheets(self):
        path = write_workbook(Path(self.directory.name) / 'financeiro.xlsx')
        result = run(path, self.engine)
        self.assertEqual(result['status'], 'complete')
        for sheet, spec in FACTS.items():
            self.assertEqual(self.scalar(f'SELECT count(*) FROM dw.{spec["table"]}'), result['rows'][sheet])

    def test_cli_and_demo_use_only_explicit_local_environment(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith(('POSTGRES_', 'FINANCE_'))}
        env.update({'POSTGRES_HOST': '127.0.0.1', 'POSTGRES_PORT': str(self.url.port),
                    'POSTGRES_DB': self.name, 'POSTGRES_USER': 'finance_test', 'POSTGRES_PASSWORD': 'ficticio'})
        path = write_workbook(Path(self.directory.name) / 'cli.xlsx')
        result = subprocess.run([sys.executable, '-X', 'utf8', 'src/ETL.py', '--input', str(path)],
                                cwd=ROOT, env=env, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertEqual(json.loads(result.stdout)['rows']['Contas_Receber'], 2)
        # Somente o banco exclusivo deste teste recebe o alias finance_demo_* no script da demo.
        demo_name = 'finance_demo_' + uuid.uuid4().hex
        with self.admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{demo_name}"'))
        try:
            env['FINANCE_DEMO_DATABASE_URL'] = self.url.set(database=demo_name).render_as_string(hide_password=False)
            demo = subprocess.run([sys.executable, '-X', 'utf8', 'scripts/run_demo.py'], cwd=ROOT,
                                  env=env, capture_output=True, timeout=60)
            self.assertEqual(demo.returncode, 0, demo.stderr.decode(errors='replace'))
            self.assertEqual(json.loads(demo.stdout)['status'], 'complete')
        finally:
            assert demo_name.startswith('finance_demo_') and len(demo_name) == 45
            with self.admin.connect() as conn:
                conn.execute(text(f'DROP DATABASE "{demo_name}" WITH (FORCE)'))


if __name__ == '__main__':
    unittest.main()
