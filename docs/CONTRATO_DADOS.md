# Contrato demonstrativo v1

Este contrato foi aprovado para profissionalizar a versão pública. Não descreve
nem pressupõe as regras ou os arquivos de uma empresa real. O Excel deve conter
exatamente as cinco abas e as colunas abaixo, sem colunas extras.

## Campos das abas

| Aba | Colunas obrigatórias |
| --- | --- |
| Faturamento | ID_Lancamento, Data_Competencia, Cliente, Unidade_Negocio, Tipo_Contrato, Receita_Bruta, Impostos, Receita_Liquida |
| Custos_Despesas | ID_Lancamento, Data_Competencia, Categoria, Tipo_Despesa, Centro_Custo, Valor |
| Orcamento | Data_Competencia, Tipo, Unidade_Negocio, Valor_Orcado |
| Contas_Receber | ID_Titulo, Cliente, Data_Emissao, Data_Vencimento, Status, Valor, Dias_Atraso |
| Metas_Negocio | Data_Competencia, Unidade_Negocio, Margem_Meta, Crescimento_Meta, Ticket_Medio_Meta |

Todas as colunas são obrigatórias e não aceitam nulo. Linhas inteiramente vazias
são ignoradas; uma aba inteira vazia interrompe a carga e preserva os dados do DW.
Abas auxiliares também são rejeitadas para não ignorar conteúdo silenciosamente.

## Tipos e convenções

- IDs: texto explícito, estável, Unicode NFKC com espaços externos removidos,
  até 200 caracteres, preservando maiúsculas e zeros iniciais.
  Não usar número da linha, nome de cliente, valor ou hash de atributos
  mutáveis para gerar a identidade. A unicidade é por fato, não entre abas.
- Nomes dimensionais: texto até 200 caracteres, Unicode NFKC, sem controles,
  espaços externos removidos, espaços repetidos reduzidos e casefold. Acentos são
  preservados. Nomes iguais são uma entidade neste contrato; homônimos exigem IDs
  cadastrais externos e uma evolução explícita do modelo.
- Datas: célula Excel de data sem horário/fuso ou texto ISO `AAAA-MM-DD`. Números
  seriais, datas inválidas e formatos ambíguos não são inferidos. Competência é a
  data informada; para períodos mensais, a origem deve convencionar o primeiro dia
  do mês. O ETL não transforma dias diferentes em uma mesma chave mensal.
- Dinheiro: `Decimal` no tratamento e `NUMERIC(18,2)` no PostgreSQL. Aceita números
  Excel ou texto decimal com ponto, sem símbolo de moeda/separador de milhar.
  Não arredonda silenciosamente valores com mais de duas casas significativas.
  Valores assinados são permitidos para representar ajustes; a interpretação
  financeira dos sinais precisa ser definida por cada aplicação.
- Faturamento: `Receita_Liquida = Receita_Bruta - Impostos`, exatamente.
- Metas: razões decimais, não texto percentual. `0.25` significa 25%.
  Margem entre -1 e 1, crescimento a partir de -1, ticket não negativo.
  Razões usam `NUMERIC(18,4)`. São limites do exemplo, não regras empresariais universais.
- Dias_Atraso: inteiro de 0 a 2147483647, informado pela origem. Não é calculado
  pelo relógio atual e o ETL não infere semântica dos textos de Status.

## Granularidade e UPSERT

| Fato | Chave de negócio | Comportamento |
| --- | --- | --- |
| faturamento | ID_Lancamento | Um lançamento por ID; atualiza dimensões e valores sem criar outra identidade. |
| custos/despesas | ID_Lancamento | Mesma política, em namespace separado do faturamento. |
| contas a receber | ID_Titulo | Valor, status, datas e atraso são atributos atualizáveis, não identidade. |
| orçamento | Data_Competencia + Tipo + Unidade_Negocio | Uma linha por combinação; duplicata no mesmo arquivo é rejeitada. |
| metas | Data_Competencia + Unidade_Negocio | Uma linha por combinação; períodos distintos são preservados. |

Linhas com IDs distintos são preservadas mesmo com dimensões e valores iguais.
Não há `DISTINCT ON` para escolher uma linha arbitrária nem soma automática de
duplicatas. Mudar uma chave composta insere outra combinação e não apaga a antiga.

O Excel é relido integralmente. O destino recebe UPSERT das chaves presentes.
Ausência de uma chave **não é exclusão**. Não há extração incremental, SCD tipo 2
ou histórico das versões anteriores dos fatos.

## Adaptação da versão anterior

A versão original não fornecia IDs estáveis de lançamentos/títulos. Não é possível
inferi-los com segurança. Arquivos antigos precisam receber esses IDs na origem.
O orçamento passa a exigir `Unidade_Negocio` explicitamente; a antiga coluna
`Categoria` não é renomeada implicitamente. Metas passam a exigir competência.
Essa mudança é intencional e foi autorizada. O projeto não migra um DW legado.

## Integridade e rastreabilidade

O DDL define nove dimensões, cinco fatos, cinco tabelas de staging, três views
analíticas, um registro de versão e um ledger de lotes bem-sucedidos.

O ledger registra UUID, horário UTC, SHA-256 dos mesmos bytes lidos do Excel,
contagens e totais de conferência. Totais de razões são somente checksums de
reconciliação, não indicadores financeiros a somar em dashboards.

Staging, dimensões, fatos e ledger são publicados na mesma transação. Chaves
estrangeiras são obrigatórias. Contagens detectam perdas nos joins e somas conferem
medidas por lote. Erros revertem a transação. Um advisory lock impede dois
publicadores deste projeto de escreverem juntos; não impede SQL externo que ignore o lock.

Dimensões são inseridas por atributo natural, sem exclusão automática. Quando um
atributo muda de nome, surge outra chave dimensional e o fato corrigido muda sua
referência. Não é gerenciamento de cadastro mestre nem histórico SCD.

O ledger não guarda linhas-fonte nem lotes que falharam, e o fato aponta para sua
última carga. Contagens e totais antigos permanecem no ledger, mas não permitem
reconstruir as versões antigas de cada lançamento.
