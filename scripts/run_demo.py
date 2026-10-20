"""Demonstração restrita a um banco local finance_demo ou finance_demo_* explícito."""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from examples.synthetic import write_workbook
from src.ETL import run
from src.config import ETLError
from src.warehouse import initialize


def main():
    engine = None
    try:
        value = os.getenv('FINANCE_DEMO_DATABASE_URL', '')
        url = make_url(value)
        if (url.drivername != 'postgresql+psycopg2' or url.query
                or url.host not in ('127.0.0.1', 'localhost', '::1')
                or not url.database or not (url.database == 'finance_demo' or url.database.startswith('finance_demo_'))):
            raise ETLError('A demonstração requer PostgreSQL local com banco finance_demo ou finance_demo_*.')
        engine = create_engine(url, connect_args={'connect_timeout': 10})
        initialize(engine)
        directory = ROOT / 'data/demo'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='finance_demo_') as work:
            result = run(write_workbook(Path(work) / 'financeiro.xlsx'), engine)
        # Resultado contém somente contagens, totais fictícios e identificadores do lote.
        (directory / 'latest_run.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result))
        return 0
    except ETLError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        print('Demonstração interrompida; configuração ou banco incompatível. Valores omitidos.', file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    sys.exit(main())
