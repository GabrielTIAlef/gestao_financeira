# Gestão Financeira — Business Intelligence e ETL dimensional

Pipeline financeiro em **Python, pandas, SQLAlchemy e PostgreSQL** que lê cinco
abas Excel, valida chaves e valores e publica um modelo dimensional com
**nove dimensões e cinco fatos**. Inclui dados fictícios, DDL versionado,
reconciliação financeira e testes de falhas com banco real.

O projeto reúne a experiência original de Business Intelligence financeiro e uma
versão pública profissionalizada para avaliação técnica. Não exige arquivos ou
bancos de uma empresa para executar a demonstração.

## Contexto e propósito do projeto original

O projeto foi desenvolvido para centralizar informações financeiras, acompanhar
a performance da operação e apoiar decisões sobre custos, receitas e
rentabilidade. A proposta original combinava automação de ETL em Python,
camadas de staging e Data Warehouse no PostgreSQL e dashboards no Power BI.

O trabalho abordou o monitoramento da saúde financeira, a análise temporal dos
indicadores, o controle de custos e despesas e a comparação entre realizado e
orçado. A separação entre origem, tratamento e consumo analítico buscava
organizar uma base que pudesse evoluir com as necessidades do negócio.

### Tecnologias e componentes da solução original

| Componente | Papel na experiência original | Representação na versão pública atual |
| --- | --- | --- |
| Excel e arquivos CSV | Fontes descritas no desenho original da solução financeira. | Entrada contratada em Excel `.xlsx`, com cinco abas; a CLI não oferece ingestão CSV. |
| Python e pandas | Extração, limpeza, normalização e tratamento temporal. | Leitura única do arquivo, validação estrita de campos e tratamento de valores com Decimal. |
| PostgreSQL e SQLAlchemy | Persistência em staging e Data Warehouse e carga com UPSERT. | DDL versionado, transações, chaves estáveis e reconciliação de contagens e valores. |
| SQL e modelagem dimensional | Organização de fatos e dimensões e preparação dos dados para BI. | Nove dimensões, cinco fatos e três views analíticas publicadas. |
| Power BI | Modelagem e dashboards para análise financeira e operacional. | Consumo analítico contextualizado; arquivos de relatório não estão publicados. |
| DAX e Power Query | Construção e tratamento da camada analítica no Power BI descritos no projeto original. | Medidas, consultas e configurações corporativas não fazem parte da demonstração pública. |

A experiência original incluiu normalização automatizada, tratamento de datas,
integração de informações financeiras, separação staging → DW → BI e trabalho
de modelagem e desempenho na camada Power BI. Isso contextualiza as decisões
do projeto, sem constituir um benchmark produtivo do código disponível.

## Dashboards e indicadores da experiência original

O README original descreve dois painéis:

| Dashboard | Finalidade | Análises descritas |
| --- | --- | --- |
| Executivo | Acompanhar a saúde financeira e apoiar decisões estratégicas. | KPIs financeiros, tendências temporais, realizado versus orçado, insights e visão consolidada da operação. |
| Operacional | Apoiar o acompanhamento financeiro e analítico do dia a dia. | Rentabilidade por cliente, despesas, inadimplência, custos por unidade, comparativos históricos e identificação de tendências e outliers. |

### Indicadores de negócio

| Área | Indicadores descritos no projeto original |
| --- | --- |
| Receita | Receita bruta, receita líquida, variação mensal (MoM), variação anual (YoY) e receita por unidade de negócio. |
| Rentabilidade | Margem bruta, margem líquida e EBITDA. |
| Gestão financeira | Ticket médio, inadimplência, aderência orçamentária e custos operacionais. |

Esses indicadores pertencem à camada analítica da experiência original.
Suas fórmulas, alocações, denominadores, regras contábeis e medidas DAX não são
inferidos a partir da amostra fictícia. A versão pública não reproduz
automaticamente todos os painéis ou indicadores acima; suas três views atuais
estão descritas na documentação de modelagem.

## Impacto profissional relatado

O relato original destaca:

- Maior visibilidade financeira e visão consolidada da operação.
- Apoio a decisões estratégicas e ao acompanhamento de custos e rentabilidade.
- Identificação de tendências e acompanhamento de indicadores financeiros.
- Organização das informações em uma base analítica estruturada.
- Separação de responsabilidades entre staging, Data Warehouse e consumo em BI,
  favorecendo a manutenção e a evolução da solução.

Esses impactos recuperam a experiência profissional descrita pelo autor.
O README original não apresenta métricas quantitativas de economia de tempo,
redução de custos ou ganho de desempenho. A proposta não acrescenta percentuais,
valores ou comparações antes/depois que não foram informados.

A frequência de acompanhamento dependia da atualização das fontes e dos
painéis. O projeto público não implementa processamento de eventos em tempo
real nem comprova uma latência produtiva.

## Experiência original e evidências públicas

| Escopo | O que o leitor pode avaliar |
| --- | --- |
| Experiência profissional original | Problema de negócio, dashboards, indicadores e impactos descritos pelo autor. Os artefatos corporativos não são distribuídos. |
| Implementação pública atual | Contrato de dados, chaves, DDL, transações, UPSERT, views e tratamento de falhas no código publicado. |
| Demonstração fictícia | Fluxo Excel → PostgreSQL, com valores esperados e arquivos gerados sem dados empresariais. |
| Validação automatizada | Testes unitários, PostgreSQL real descartável e execuções verificáveis no GitHub Actions. |

As melhorias técnicas abaixo preservam a finalidade financeira do projeto e
tornam sua versão pública reproduzível. Elas não correspondem a uma nova
homologação do ambiente corporativo.

## Confiabilidade da implementação pública

Lançamentos distintos podem ter as mesmas dimensões. Deduplicar por cliente,
data e categoria pode eliminar valores legítimos. Da mesma forma, identificar
um título pelo seu valor ou status gera duplicação quando esses atributos mudam.

Este ETL usa IDs estáveis para lançamentos e títulos, valida o contrato de entrada
e reconcilia contagens e valores após os joins e UPSERTs. Staging, dimensões,
fatos e controle do lote ficam na mesma transação: uma falha reverte a publicação.

```mermaid
flowchart LR
    E[Excel fictício: cinco abas] --> V[Contrato: IDs, datas e Decimal]
    V --> T[Transação PostgreSQL com advisory lock]
    T --> S[Staging]
    S --> D[Nove dimensões]
    D --> F[Cinco fatos com UPSERT]
    F --> R[Reconciliação de contagens e valores]
    R --> C[Commit e ledger do lote]
    C --> B[Views SQL para consumo analítico]
```

## Escopo financeiro

| Fato | Chave de negócio |
| --- | --- |
| Faturamento | ID_Lancamento |
| Custos/despesas | ID_Lancamento, em namespace separado do faturamento |
| Contas a receber | ID_Titulo |
| Orçamento | Data_Competencia + Tipo + Unidade_Negocio |
| Metas | Data_Competencia + Unidade_Negocio |

IDs distintos são preservados mesmo com valores e dimensões iguais. Reenviar a
mesma chave atualiza seus atributos. Ausência no Excel não exclui a linha do DW.
Duplicatas ambíguas dentro da mesma aba são rejeitadas, sem descarte ou soma automática.

O modelo é uma **constelação de fatos com dimensões compartilhadas**.
Consulte o [contrato das abas](docs/CONTRATO_DADOS.md) e a
[modelagem](docs/MODELAGEM.md) para campos, granularidade e relacionamentos.

## Demonstração reproduzível

Roteiro validado no Windows com Python 3.12.14 e PostgreSQL 18.6. Na raiz do
repositório, usando PowerShell e Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/generate_sample.py
```

O gerador cria `data/demo/financeiro.xlsx`, sem sobrescrever arquivos existentes.
São 3 lançamentos de faturamento, 3 de custos, 2 orçamentos, 2 títulos e 2 metas.
Há lançamentos com a mesma combinação dimensional e títulos de valores iguais,
identificados por IDs diferentes.

Para executar a suíte completa e a demo, obtenha primeiro os binários portáteis
do PostgreSQL conforme o [guia de reprodução](docs/REPRODUCAO.md):

```powershell
$PgBin = (Resolve-Path '.local-test\runtime\pgsql\bin').Path
.\.venv\Scripts\python.exe -X utf8 scripts/validate_postgres.py --pg-bin "$PgBin" --demo
```

O script cria PostgreSQL e bancos descartáveis locais, testa as cargas e encerra
o servidor. Não instala serviço Windows e não precisa de `.env` ou contas
corporativas. O resumo fictício fica em `data/demo/latest_run.json` e os logs
locais em `.local-test/`. Binários precisam ser obtidos antes; não há download
automático no script.

Totais esperados da amostra: receita bruta **170.00**, impostos **17.00**,
receita líquida **153.00**, custos **35.30**, orçamento **250.00** e títulos **200.20**.
Esses números são fictícios, não resultados de uma operação real.

## Confiabilidade e testes

A suíte tem **55 testes: 30 unitários/configuração e 25 com PostgreSQL real**.
Em duas instalações novas no Windows, todos passaram, sem erros, falhas ou
testes ignorados. Veja [resultados e limites](docs/VALIDACAO.md).

Os testes verificam, entre outros comportamentos:

- Reprocessamento sem duplicação de chaves de negócio.
- Atualização de valor, status e atraso sem criar outro título.
- Preservação de lançamentos diferentes com dimensões iguais.
- Precisão monetária, totais, FKs e restrições de unicidade.
- Rollback de staging, dimensões, fatos e ledger após falhas.
- Detecção de perda em joins e divergência de valores.
- Concorrência, schema incompatível e recusa de objetos legados.
- Fluxo Excel → PostgreSQL e execução da CLI e da demonstração.

Sem PostgreSQL é possível executar:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/run_tests.py
```

Nesse modo os casos PostgreSQL são informados como ignorados. **Não equivale à
validação completa.** O workflow de GitHub Actions usa PostgreSQL obrigatório e
falha se houver testes omitidos. Houve execução aprovada no GitHub/Linux após
a publicação do histórico sanitizado:
[registro da execução](https://github.com/GabrielTIAlef/gestao_financeira/actions/runs/39421743949).
O CI executa em propostas para a `main` e em atualizações dessa branch;
não há implantação automática de ambiente produtivo.

## Organização

| Caminho | Responsabilidade |
| --- | --- |
| [src/ETL.py](src/ETL.py) | CLI e coordenação, sem carga na importação. |
| [src/contracts.py](src/contracts.py) | Leitura única do Excel, normalização e validação. |
| [src/model.py](src/model.py) | Mapeamento fechado entre origem, dimensões e fatos. |
| [src/warehouse.py](src/warehouse.py) | Inicialização, transação, locks, UPSERT e reconciliação. |
| [src/config.py](src/config.py) | Configuração por ambiente, sem credenciais predefinidas. |
| [sql/001_schema.sql](sql/001_schema.sql) | DDL, chaves, restrições, índices e três views analíticas. |
| [examples/synthetic.py](examples/synthetic.py) | Fonte inteiramente fictícia e gerador Excel. |
| [scripts/](scripts/) e [tests/](tests/) | Demonstração e validação automatizada. |
| [.github/workflows/tests.yml](.github/workflows/tests.yml) | CI validado com Python e PostgreSQL descartável. |

## Configuração própria

Para adaptar o ETL a dados sob sua autorização, veja [.env.example](.env.example),
[SECURITY.md](SECURITY.md) e o [procedimento](docs/REPRODUCAO.md).
`python src/ETL.py --init` inicializa e encerra; a carga é outro comando:
`python src/ETL.py --input caminho/arquivo.xlsx`.

A versão anterior não fornecia IDs estáveis nem DDL reproduzível. O novo contrato
exige adaptação explícita do arquivo de origem e banco novo. Não há migração
automática do banco ou dos arquivos de uma empresa anterior.

## Limites e escolhas

- A origem é relida integralmente. UPSERT no destino não é extração incremental.
- As cargas não excluem fatos ausentes, não criam histórico SCD e não guardam
  versões antigas das linhas. O ledger registra métricas de lotes bem-sucedidos.
- Dimensões por nome são um contrato demonstrativo; homônimos precisam de IDs
  cadastrais numa evolução do projeto.
- Valores usam uma unidade monetária comum, sem conversão cambial. Convenções
  de sinais e percentuais estão no contrato, não são regras de uma empresa real.
- Não há benchmark com volume produtivo, homologação empresarial ou teste macOS.
- Os dashboards e as medidas DAX da experiência original não estão publicados.
  As views públicas não calculam EBITDA nem reproduzem regras contábeis privadas.
  O projeto não implementa modelos preditivos.
- As branches tiveram o histórico sanitizado, mas a referência interna da proposta
  #1 ainda mantém ancestralidade anterior. O tratamento de referências e caches
  pelo suporte do GitHub permanece separado; a limpeza não revoga credenciais.

## Competências demonstradas

Na experiência original: compreensão de necessidades financeiras, organização de
indicadores, modelagem para consumo em Power BI, análise de rentabilidade e
comunicação de informações para apoiar decisões.

Na implementação pública: Python, pandas, SQL, PostgreSQL, modelagem dimensional,
chaves de negócio, UPSERT, transações, reconciliação financeira, testes de
integração, configuração por ambiente e integração contínua.

O conjunto apresenta competências para Análise de Dados, BI Pleno e Analytics
Engineering, com separação entre experiência profissional, funcionalidades do
código e evidências reproduzíveis.
