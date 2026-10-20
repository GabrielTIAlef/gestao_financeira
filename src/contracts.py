"""Contrato financeiro explícito: sem inferir IDs, datas ou agregações."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import unicodedata

import pandas as pd

from src.config import ETLError

SHEETS = {
    'Faturamento': {'ID_Lancamento': 'id', 'Data_Competencia': 'date', 'Cliente': 'name',
                    'Unidade_Negocio': 'name', 'Tipo_Contrato': 'name', 'Receita_Bruta': 'money',
                    'Impostos': 'money', 'Receita_Liquida': 'money'},
    'Custos_Despesas': {'ID_Lancamento': 'id', 'Data_Competencia': 'date', 'Categoria': 'name',
                       'Tipo_Despesa': 'name', 'Centro_Custo': 'name', 'Valor': 'money'},
    'Orcamento': {'Data_Competencia': 'date', 'Tipo': 'name', 'Unidade_Negocio': 'name',
                  'Valor_Orcado': 'money'},
    'Contas_Receber': {'ID_Titulo': 'id', 'Cliente': 'name', 'Data_Emissao': 'date',
                       'Data_Vencimento': 'date', 'Status': 'name', 'Valor': 'money',
                       'Dias_Atraso': 'integer'},
    'Metas_Negocio': {'Data_Competencia': 'date', 'Unidade_Negocio': 'name',
                      'Margem_Meta': 'ratio', 'Crescimento_Meta': 'ratio',
                      'Ticket_Medio_Meta': 'money'},
}
KEYS = {'Faturamento': ('ID_Lancamento',), 'Custos_Despesas': ('ID_Lancamento',),
        'Contas_Receber': ('ID_Titulo',),
        'Orcamento': ('Data_Competencia', 'Tipo', 'Unidade_Negocio'),
        'Metas_Negocio': ('Data_Competencia', 'Unidade_Negocio')}
MEASURES = {sheet: tuple(col for col, kind in fields.items() if kind in ('money', 'ratio'))
            for sheet, fields in SHEETS.items()}


def convert(value, kind):
    if value is None or pd.isna(value) or isinstance(value, bool):
        raise ValueError('valor obrigatório ausente ou booleano')
    if kind in ('id', 'name'):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('texto obrigatório')
        value = unicodedata.normalize('NFKC', value).strip()
        if any(unicodedata.category(c).startswith('C') for c in value) or len(value) > 200:
            raise ValueError('texto inválido ou muito longo')
        return ' '.join(value.split()).casefold() if kind == 'name' else value
    if kind == 'date':
        if isinstance(value, datetime):
            if value.tzinfo is not None or value.time() != datetime.min.time():
                raise ValueError('data deve ser sem horário ou fuso')
            return value.date()
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('data deve ser célula de data ou ISO AAAA-MM-DD')
        return date.fromisoformat(value)
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError('número não finito')
        scale = {'money': 2, 'ratio': 4, 'integer': 0}[kind]
        quantum = Decimal(1).scaleb(-scale)
        if number != number.quantize(quantum):
            raise ValueError('precisão excedida; arredondamento não é automático')
        if kind == 'integer':
            if number < 0 or number > 2147483647:
                raise ValueError('inteiro fora dos limites')
            return int(number)
        if abs(number) >= Decimal(10) ** (18 - scale):
            raise ValueError('número fora dos limites')
        return number.quantize(quantum)
    except (InvalidOperation, TypeError, OverflowError):
        raise ValueError('número inválido') from None


def validate(frames):
    if set(frames) != set(SHEETS):
        raise ETLError('O arquivo deve conter exatamente as cinco abas do contrato.')
    result = {}
    for sheet, fields in SHEETS.items():
        frame = frames[sheet].dropna(how='all').copy()
        if frame.empty or frame.columns.duplicated().any() or set(frame.columns) != set(fields):
            raise ETLError(f'{sheet}: lote vazio ou colunas incompatíveis com o contrato.')
        records = []
        for index, row in enumerate(frame.to_dict('records'), 2):
            record = {}
            for column, kind in fields.items():
                try:
                    record[column] = convert(row[column], kind)
                except (ValueError, TypeError, OverflowError):
                    raise ETLError(f'{sheet}: coluna {column}, linha {index}: valor inválido.') from None
            if sheet == 'Faturamento' and record['Receita_Bruta'] - record['Impostos'] != record['Receita_Liquida']:
                raise ETLError(f'{sheet}: linha {index}: receita líquida não reconcilia.')
            if sheet == 'Metas_Negocio' and (
                    not Decimal('-1') <= record['Margem_Meta'] <= Decimal('1')
                    or record['Crescimento_Meta'] < -1 or record['Ticket_Medio_Meta'] < 0):
                raise ETLError(f'{sheet}: linha {index}: meta fora do contrato demonstrativo.')
            records.append(record)
        clean = pd.DataFrame(records, columns=fields)
        if clean.duplicated(list(KEYS[sheet])).any():
            raise ETLError(f'{sheet}: chave de negócio duplicada; carga rejeitada.')
        result[sheet] = clean
    return result


def read_workbook(path):
    try:
        path = Path(path)
        if path.suffix.lower() != '.xlsx':
            raise ETLError('A entrada deve ser um arquivo .xlsx.')
        content = path.read_bytes()
        with pd.ExcelFile(BytesIO(content), engine='openpyxl') as book:
            # Uma só leitura dos bytes evita reconciliar hash de outra versão do arquivo.
            frames = {sheet: pd.read_excel(book, sheet_name=sheet, dtype=object,
                                          keep_default_na=False) for sheet in book.sheet_names}
    except ETLError:
        raise
    except Exception:
        raise ETLError('Não foi possível ler o Excel; verifique arquivo e permissões.') from None
    # Excel vazio costuma ser string vazia com keep_default_na=False. Remover apenas linhas inteiras vazias.
    frames = {sheet: frame.replace('', None).dropna(how='all') for sheet, frame in frames.items()}
    return validate(frames), sha256(content).hexdigest()


def totals(frames):
    return {sheet: {col: str(sum(frame[col], Decimal('0'))) for col in MEASURES[sheet]}
            for sheet, frame in frames.items()}
