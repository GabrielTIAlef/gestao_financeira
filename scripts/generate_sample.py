"""Gera um Excel fictício; não sobrescreve arquivos existentes."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from examples.synthetic import write_workbook


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/demo/financeiro.xlsx')
    args = parser.parse_args()
    try:
        write_workbook(args.output)
        print('Excel fictício gerado; nenhuma conexão foi realizada.')
    except (OSError, ValueError):
        sys.exit('Não foi possível gerar a amostra; confira destino e arquivo existente.')
