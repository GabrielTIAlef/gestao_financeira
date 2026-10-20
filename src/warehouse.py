"""Carga PostgreSQL em uma transação, com UPSERT e reconciliação por lote."""
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import logging
import re
import uuid

from sqlalchemy import inspect, text

from src.config import ETLError, ROOT
from src.contracts import MEASURES, SHEETS, totals, validate
from src.model import DIMENSIONS, FACTS

LOG = logging.getLogger(__name__)
LOCK_ID = 724193820
DDL = ROOT / 'sql/001_schema.sql'


def _ddl_hash():
    # Normalizar finais de linha para funcionar com checkout Windows e Linux.
    return sha256(DDL.read_text(encoding='utf-8').replace('\r\n', '\n').encode()).hexdigest()


def _lock(conn):
    if conn.dialect.name != 'postgresql':
        raise ETLError('O DW requer PostgreSQL.')
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))
    if not conn.execute(text('SELECT pg_try_advisory_xact_lock(:key)'), {'key': LOCK_ID}).scalar_one():
        raise ETLError('Outra carga ou inicialização financeira está em execução.')


def _check_schema(conn):
    try:
        version = conn.execute(text('SELECT version, ddl_sha256 FROM dw.schema_version')).one()
        if version.version != 1 or version.ddl_sha256 != _ddl_hash():
            raise ETLError('Schema incompatível; migração explícita necessária.')
    except ETLError:
        raise
    except Exception:
        raise ETLError('Schema ausente ou incompatível; inicialize apenas um banco novo.') from None


def initialize(engine):
    """Cria somente em schemas vazios; nunca migra ou apaga um DW legado."""
    try:
        with engine.begin() as conn:
            _lock(conn)
            inspector = inspect(conn)
            if inspector.has_table('schema_version', schema='dw'):
                _check_schema(conn)
                return
            existing = set(inspector.get_schema_names())
            if any(schema in existing and (
                    inspector.get_table_names(schema=schema) or inspector.get_view_names(schema=schema))
                   for schema in ('stg', 'dw')):
                raise ETLError('Schemas stg/dw já contêm objetos; migração explícita necessária.')
            for statement in DDL.read_text(encoding='utf-8').split(';'):
                if statement.strip():
                    conn.execute(text(statement))
            conn.execute(text('INSERT INTO dw.schema_version(version, ddl_sha256) VALUES (1, :hash)'),
                         {'hash': _ddl_hash()})
    except ETLError:
        raise
    except Exception:
        raise ETLError('Falha ao inicializar o schema; alterações revertidas.') from None


def _dimensions(conn, frames):
    dates = set()
    for sheet, frame in frames.items():
        for column, kind in SHEETS[sheet].items():
            if kind == 'date':
                dates.update(frame[column])
    params = [{'id': d.year * 10000 + d.month * 100 + d.day, 'date': d,
               'year': d.year, 'month': d.month, 'day': d.day} for d in sorted(dates)]
    conn.execute(text('INSERT INTO dw.dim_tempo(data_id, data, ano, mes, dia) '
                      'VALUES (:id, :date, :year, :month, :day) ON CONFLICT(data) DO NOTHING'), params)
    for source, (table, _, natural) in DIMENSIONS.items():
        values = sorted({value for frame in frames.values() if source in frame for value in frame[source]})
        if values:
            conn.execute(text(f'INSERT INTO dw.{table}({natural}) VALUES (:value) '
                              f'ON CONFLICT({natural}) DO NOTHING'), [{'value': v} for v in values])


def _fact_sql(sheet, spec):
    # Todos os identificadores vêm do contrato fechado em model.py, nunca do Excel.
    columns, expressions, joins = [], [], []
    for source, target in spec['ids'].items():
        columns.append(target)
        expressions.append(f's."{source}"')
    for index, (source, target) in enumerate(spec['dimensions'].items()):
        alias = f'd{index}'
        if SHEETS[sheet][source] == 'date':
            table, pk, natural = 'dim_tempo', 'data_id', 'data'
        else:
            table, pk, natural = DIMENSIONS[source]
        columns.append(target)
        expressions.append(f'{alias}.{pk}')
        joins.append(f'JOIN dw.{table} {alias} ON {alias}.{natural} = s."{source}"')
    for source, target in spec['measures'].items():
        columns.append(target)
        expressions.append(f's."{source}"')
    columns += ['batch_id', 'tempo_carga']
    expressions += ['s.batch_id', 's.tempo_carga']
    updates = ', '.join(f'{c} = EXCLUDED.{c}' for c in columns if c not in spec['keys'])
    return (f'INSERT INTO dw.{spec["table"]} ({", ".join(columns)}) '
            f'SELECT {", ".join(expressions)} FROM stg."{sheet}" s {" ".join(joins)} '
            f'ON CONFLICT ({", ".join(spec["keys"])}) DO UPDATE SET {updates}')


def _reconcile(conn, frames, batch):
    for sheet, spec in FACTS.items():
        frame = frames[sheet]
        measures = [spec['measures'][c] for c in MEASURES[sheet]]
        sums = ', '.join(f'COALESCE(SUM({col}), 0) AS {col}' for col in measures)
        row = conn.execute(text(f'SELECT count(*) AS rows, {sums} FROM dw.{spec["table"]} '
                                'WHERE batch_id = :batch'), {'batch': batch}).mappings().one()
        if row['rows'] != len(frame):
            raise ETLError(f'{sheet}: contagem após joins/UPSERT não reconcilia.')
        for source in MEASURES[sheet]:
            if row[spec['measures'][source]] != sum(frame[source], Decimal('0')):
                raise ETLError(f'{sheet}: totais financeiros não reconciliam.')


def publish(engine, frames, source_hash):
    """Revalida entradas antes de escrever; não registra dados das linhas."""
    frames = validate(frames)
    if not isinstance(source_hash, str) or not re.fullmatch('[0-9a-f]{64}', source_hash):
        raise ETLError('Hash da origem inválido.')
    batch = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)
    phase = 'lock'
    try:
        with engine.begin() as conn:
            _lock(conn)
            _check_schema(conn)
            phase = 'staging'
            conn.execute(text('INSERT INTO dw.etl_batch(batch_id, tempo_carga, source_sha256, '
                              'source_counts, source_totals) VALUES '
                              '(:batch, :timestamp, :hash, CAST(:counts AS jsonb), CAST(:totals AS jsonb))'),
                         {'batch': batch, 'timestamp': timestamp, 'hash': source_hash,
                          'counts': json.dumps({s: len(f) for s, f in frames.items()}),
                          'totals': json.dumps(totals(frames))})
            for sheet in SHEETS:
                conn.execute(text(f'DELETE FROM stg."{sheet}"'))
                frame = frames[sheet].copy()
                frame['batch_id'], frame['tempo_carga'] = batch, timestamp
                # Tabelas pré-criadas pelo DDL; não usar replace nem nomes recebidos do arquivo.
                frame.to_sql(sheet, conn, schema='stg', if_exists='append', index=False, chunksize=500)
                count = conn.execute(text(f'SELECT count(*) FROM stg."{sheet}"')).scalar_one()
                if count != len(frame):
                    raise ETLError(f'{sheet}: staging não reconcilia.')
            phase = 'dimensões'
            _dimensions(conn, frames)
            phase = 'fatos'
            for sheet, spec in FACTS.items():
                conn.execute(text(_fact_sql(sheet, spec)))
            phase = 'reconciliação'
            _reconcile(conn, frames, batch)
        result = {'status': 'complete', 'batch_id': batch, 'source_sha256': source_hash,
                  'rows': {s: len(f) for s, f in frames.items()}, 'totals': totals(frames)}
        LOG.info('Carga concluída: batch_id=%s contagens=%s', batch, result['rows'])
        return result
    except ETLError:
        raise
    except Exception:
        LOG.error('Carga revertida: batch_id=%s etapa=%s', batch, phase)
        raise ETLError(f'Carga interrompida na etapa {phase}; transação revertida.') from None
