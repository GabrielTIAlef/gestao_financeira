# Reprodução local com dados fictícios

O roteiro foi validado em Windows x86-64, Python 3.12.14 e PostgreSQL 18.6.
Não exige planilhas, `.env`, senhas ou bancos da antiga empresa.

## Instalar

Na raiz do repositório, com Python 3.12 selecionado no PATH:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
```

O lockfile foi gerado a partir das dependências resolvidas, não copiado de outro
projeto. A instalação requer acesso ao índice de pacotes.

## Gerar somente o Excel

```powershell
.\.venv\Scripts\python.exe scripts/generate_sample.py
```

Gera `data/demo/financeiro.xlsx`, ignorado pelo Git. Não sobrescreve um arquivo
existente. Para outro destino, use `--output data/demo/outra_amostra.xlsx`.
O gerador não acessa o banco. As colunas estão em [CONTRATO_DADOS.md](CONTRATO_DADOS.md).

## Executar toda a validação com PostgreSQL temporário

Obtenha os binários Windows pela [página do PostgreSQL](https://www.postgresql.org/download/windows/)
e pelo distribuidor [EDB](https://www.enterprisedb.com/download-postgresql-binaries).
Extraia a distribuição completa em `.local-test/runtime/`, de modo que existam
`pgsql/bin/initdb.exe`, `pg_ctl.exe` e `postgres.exe`. A validação utilizou 18.6.
Não há download automático de banco pelo script.

```powershell
$PgBin = (Resolve-Path '.local-test\runtime\pgsql\bin').Path
.\.venv\Scripts\python.exe -X utf8 scripts/validate_postgres.py --pg-bin "$PgBin" --demo
```

O script:

1. Cria um cluster novo em `.local-test/finance_pg_*`, escolhe uma porta livre e
   escuta somente em `127.0.0.1`, sem instalar serviço Windows.
2. Usa a conta fictícia `finance_test`, com trust apenas no cluster descartável.
3. Remove configurações corporativas e financeiras herdadas do ambiente entregue
   aos processos de teste. Os testes não usam `.env` de produção.
4. Executa a suíte com `--require-postgresql`: ignorar integração não conta como sucesso.
5. Cada teste cria bancos exclusivos e os remove após uso.
6. Cria `finance_demo`, inicializa o schema e executa a demonstração fictícia.
7. Encerra o servidor em `finally`. Conserva cluster encerrado e logs em `.local-test/`.

Consulte `.local-test/last_validation.json` para o resumo e o caminho do cluster
para diagnóstico. Não versionar cluster, logs ou ambientes virtuais.

`data/demo/latest_run.json` contém o resumo fictício da demonstração. A amostra
tem 3 lançamentos de faturamento, 3 de custos, 2 orçamentos, 2 títulos e 2 metas.
Valores esperados: receita bruta 170.00, impostos 17.00, receita líquida 153.00,
custos 35.30, orçamento 250.00 e títulos 200.20.

## Executar sem PostgreSQL

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/run_tests.py
```

Os testes de PostgreSQL serão explicitamente ignorados. Isso não equivale à
validação completa. O número executado inclui também os casos ignorados;
consulte sempre a contagem de `skipped`.

## Usar um banco de demonstração local já criado

Somente para um banco sob sua autorização, sem objetos legados:

```powershell
$env:FINANCE_DEMO_DATABASE_URL = 'postgresql+psycopg2://USUARIO_LOCAL@127.0.0.1:PORTA/finance_demo'
.\.venv\Scripts\python.exe -X utf8 scripts/run_demo.py
```

A URL precisa ter host local, sem parâmetros de query, e banco `finance_demo` ou
`finance_demo_*`. A demo inicializa o schema e faz UPSERT dos IDs fictícios; não
execute em banco com dados que você queira preservar. Não lê configuração `.env`.

## Operação explícita com arquivo próprio

É uma adaptação fora da demo, exige o contrato v1 e autorização para os dados/banco.
Copie `.env.example` para `.env` local e preencha com suas próprias configurações.

```powershell
.\.venv\Scripts\python.exe src/ETL.py --init
.\.venv\Scripts\python.exe src/ETL.py --input data/demo/financeiro.xlsx
```

`--init` apenas inicializa e encerra; a carga é um comando separado.
Sem `--input`, usa `FINANCE_INPUT_PATH`. Nunca aponta para caminhos pessoais
predefinidos. A inicialização recusa schemas legados; não execute uma migração
de produção com este comando. Leia [SECURITY.md](../SECURITY.md).

## Linux e CI

O workflow usa Ubuntu 24.04, Python 3.12 e o serviço PostgreSQL 18 do runner.
Instala o lockfile, executa `pip check`, registra versões e usa:

```bash
python scripts/run_tests.py --require-postgresql --result-path .local-test/ci-result.json
```

As variáveis de teste são definidas somente para o container local descartável.
O workflow não usa secrets corporativos. A configuração foi preparada localmente;
a aprovação em GitHub/Linux só poderá ser registrada após publicação autorizada.
