"""Entrada coordenada do ETL financeiro. Importar não abre arquivos ou conexões."""
import argparse
import json
import logging
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine

from src.config import ETLError, database_url, input_path
from src.contracts import read_workbook
from src.warehouse import initialize, publish


def run(path, engine):
    frames, source_hash = read_workbook(path)
    return publish(engine, frames, source_hash)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', help='Excel .xlsx compatível com docs/CONTRATO_DADOS.md.')
    parser.add_argument('--init', action='store_true', help='Somente inicializar um banco novo e encerrar.')
    args = parser.parse_args()
    engine = None
    try:
        path = None if args.init else input_path(args.input)
        engine = create_engine(database_url(), pool_pre_ping=True, connect_args={'connect_timeout': 10})
        if args.init:
            initialize(engine)
            print(json.dumps({'status': 'schema_ready'}))
        else:
            print(json.dumps(run(path, engine), ensure_ascii=False))
        return 0
    except ETLError as error:
        logging.error('%s', error)
        return 1
    except Exception:
        logging.error('Execução interrompida; verifique configuração e permissões. Valores sensíveis omitidos.')
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    sys.exit(main())
