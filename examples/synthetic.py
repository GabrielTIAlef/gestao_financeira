"""Cinco abas fictícias com IDs explícitos e lançamentos de mesma combinação dimensional."""
from pathlib import Path

import pandas as pd


def frames():
    return {
        'Faturamento': pd.DataFrame([
            ['F001', '2026-01-01', 'Cliente Fictício A', 'Unidade A', 'Mensal', '100.10', '10.01', '90.09'],
            ['F002', '2026-01-01', 'Cliente Fictício A', 'Unidade A', 'Mensal', '49.90', '4.99', '44.91'],
            ['F003', '2026-01-01', 'Cliente Fictício B', 'Unidade B', 'Avulso', '20.00', '2.00', '18.00'],
        ], columns=['ID_Lancamento', 'Data_Competencia', 'Cliente', 'Unidade_Negocio', 'Tipo_Contrato',
                    'Receita_Bruta', 'Impostos', 'Receita_Liquida']),
        'Custos_Despesas': pd.DataFrame([
            ['C001', '2026-01-01', 'Serviços', 'Variável', 'Centro A', '10.10'],
            ['C002', '2026-01-01', 'Serviços', 'Variável', 'Centro A', '20.20'],
            ['C003', '2026-01-01', 'Infraestrutura', 'Fixa', 'Centro B', '5.00'],
        ], columns=['ID_Lancamento', 'Data_Competencia', 'Categoria', 'Tipo_Despesa', 'Centro_Custo', 'Valor']),
        'Orcamento': pd.DataFrame([
            ['2026-01-01', 'Receita', 'Unidade A', '200.00'],
            ['2026-01-01', 'Receita', 'Unidade B', '50.00'],
        ], columns=['Data_Competencia', 'Tipo', 'Unidade_Negocio', 'Valor_Orcado']),
        'Contas_Receber': pd.DataFrame([
            ['T001', 'Cliente Fictício A', '2026-01-01', '2026-01-31', 'Aberto', '100.10', 0],
            ['T002', 'Cliente Fictício A', '2026-01-01', '2026-01-31', 'Aberto', '100.10', 0],
        ], columns=['ID_Titulo', 'Cliente', 'Data_Emissao', 'Data_Vencimento', 'Status', 'Valor', 'Dias_Atraso']),
        'Metas_Negocio': pd.DataFrame([
            ['2026-01-01', 'Unidade A', '0.2500', '0.1000', '100.00'],
            ['2026-01-01', 'Unidade B', '0.3000', '0.2000', '50.00'],
        ], columns=['Data_Competencia', 'Unidade_Negocio', 'Margem_Meta', 'Crescimento_Meta', 'Ticket_Medio_Meta']),
    }


def write_workbook(path, source=None):
    path = Path(path)
    if path.exists():
        raise FileExistsError('Arquivo já existe; escolha outro destino para a amostra.')
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for sheet, frame in (frames() if source is None else source).items():
            frame.to_excel(writer, sheet_name=sheet, index=False)
    return path
