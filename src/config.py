"""Configuração explícita, sem credenciais ou acesso a serviços na importação."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL

ROOT = Path(__file__).resolve().parents[1]


class ETLError(RuntimeError):
    """Erro operacional seguro para logs e linha de comando."""


def database_url():
    load_dotenv(ROOT / '.env', override=False)
    required = ('POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD')
    if any(not os.getenv(key, '').strip() for key in required):
        raise ETLError('Configuração PostgreSQL incompleta; consulte .env.example.')
    try:
        port = int(os.getenv('POSTGRES_PORT', '5432'))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise ETLError('POSTGRES_PORT inválida.') from None
    return URL.create('postgresql+psycopg2', username=os.environ['POSTGRES_USER'],
                      password=os.environ['POSTGRES_PASSWORD'], host=os.environ['POSTGRES_HOST'],
                      port=port, database=os.environ['POSTGRES_DB'])


def input_path(value=None):
    load_dotenv(ROOT / '.env', override=False)
    value = value or os.getenv('FINANCE_INPUT_PATH')
    if not value:
        raise ETLError('Informe --input ou FINANCE_INPUT_PATH.')
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path
