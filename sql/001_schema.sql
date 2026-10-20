-- Contrato demonstrativo v1. Inicialização somente em schemas vazios.

CREATE SCHEMA IF NOT EXISTS stg;

CREATE SCHEMA IF NOT EXISTS dw;

CREATE TABLE dw.schema_version(version integer PRIMARY KEY CHECK(version = 1), ddl_sha256 char(64) NOT NULL);

CREATE TABLE dw.etl_batch(batch_id uuid PRIMARY KEY, tempo_carga timestamptz NOT NULL, source_sha256 char(64) NOT NULL, source_counts jsonb NOT NULL, source_totals jsonb NOT NULL);

CREATE TABLE dw.dim_tempo(data_id integer PRIMARY KEY, data date NOT NULL UNIQUE,
 ano integer NOT NULL, mes integer NOT NULL CHECK(mes BETWEEN 1 AND 12), dia integer NOT NULL CHECK(dia BETWEEN 1 AND 31),
 CHECK(data_id = ano * 10000 + mes * 100 + dia), CHECK(ano = EXTRACT(YEAR FROM data)),
 CHECK(mes = EXTRACT(MONTH FROM data)), CHECK(dia = EXTRACT(DAY FROM data)));

CREATE TABLE dw.dim_cliente(cliente_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, cliente text NOT NULL UNIQUE CHECK(length(cliente) BETWEEN 1 AND 200));

CREATE TABLE dw.dim_unidade_negocio(unidade_negocio_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, unidade_negocio text NOT NULL UNIQUE CHECK(length(unidade_negocio) BETWEEN 1 AND 200));

CREATE TABLE dw.dim_tipo_contrato(tipo_contrato_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, tipo_contrato text NOT NULL UNIQUE CHECK(length(tipo_contrato) BETWEEN 1 AND 200));

CREATE TABLE dw.dim_categoria(categoria_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, categoria text NOT NULL UNIQUE CHECK(length(categoria) BETWEEN 1 AND 200));

CREATE TABLE dw.dim_tipo_despesa(tipo_despesa_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, tipo_despesa text NOT NULL UNIQUE CHECK(length(tipo_despesa) BETWEEN 1 AND 200));

CREATE TABLE dw.dim_centro_custo(centro_custo_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, centro_custo text NOT NULL UNIQUE CHECK(length(centro_custo) BETWEEN 1 AND 200));

CREATE TABLE dw.dim_status(status_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, status text NOT NULL UNIQUE CHECK(length(status) BETWEEN 1 AND 200));

CREATE TABLE dw.dim_tipo_orcamento(tipo_orcamento_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, tipo text NOT NULL UNIQUE CHECK(length(tipo) BETWEEN 1 AND 200));

CREATE TABLE stg."Faturamento" (
  "ID_Lancamento" text NOT NULL,
  "Data_Competencia" date NOT NULL,
  "Cliente" text NOT NULL,
  "Unidade_Negocio" text NOT NULL,
  "Tipo_Contrato" text NOT NULL,
  "Receita_Bruta" numeric(18,2) NOT NULL,
  "Impostos" numeric(18,2) NOT NULL,
  "Receita_Liquida" numeric(18,2) NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE ("ID_Lancamento")
);

CREATE TABLE stg."Custos_Despesas" (
  "ID_Lancamento" text NOT NULL,
  "Data_Competencia" date NOT NULL,
  "Categoria" text NOT NULL,
  "Tipo_Despesa" text NOT NULL,
  "Centro_Custo" text NOT NULL,
  "Valor" numeric(18,2) NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE ("ID_Lancamento")
);

CREATE TABLE stg."Orcamento" (
  "Data_Competencia" date NOT NULL,
  "Tipo" text NOT NULL,
  "Unidade_Negocio" text NOT NULL,
  "Valor_Orcado" numeric(18,2) NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE ("Data_Competencia", "Tipo", "Unidade_Negocio")
);

CREATE TABLE stg."Contas_Receber" (
  "ID_Titulo" text NOT NULL,
  "Cliente" text NOT NULL,
  "Data_Emissao" date NOT NULL,
  "Data_Vencimento" date NOT NULL,
  "Status" text NOT NULL,
  "Valor" numeric(18,2) NOT NULL,
  "Dias_Atraso" integer NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE ("ID_Titulo")
);

CREATE TABLE stg."Metas_Negocio" (
  "Data_Competencia" date NOT NULL,
  "Unidade_Negocio" text NOT NULL,
  "Margem_Meta" numeric(18,4) NOT NULL,
  "Crescimento_Meta" numeric(18,4) NOT NULL,
  "Ticket_Medio_Meta" numeric(18,2) NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE ("Data_Competencia", "Unidade_Negocio")
);

CREATE TABLE dw.fato_faturamento (
  row_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_lancamento text NOT NULL CHECK(length(id_lancamento) BETWEEN 1 AND 200),
  data_id integer NOT NULL REFERENCES dw.dim_tempo(data_id),
  cliente_id bigint NOT NULL REFERENCES dw.dim_cliente(cliente_id),
  unidade_negocio_id bigint NOT NULL REFERENCES dw.dim_unidade_negocio(unidade_negocio_id),
  tipo_contrato_id bigint NOT NULL REFERENCES dw.dim_tipo_contrato(tipo_contrato_id),
  receita_bruta numeric(18,2) NOT NULL,
  impostos numeric(18,2) NOT NULL,
  receita_liquida numeric(18,2) NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE (id_lancamento),
  CHECK(receita_liquida = receita_bruta - impostos)
);

CREATE INDEX ix_fato_faturamento_batch ON dw.fato_faturamento(batch_id);

CREATE INDEX ix_fato_faturamento_data_id ON dw.fato_faturamento(data_id);

CREATE INDEX ix_fato_faturamento_cliente_id ON dw.fato_faturamento(cliente_id);

CREATE INDEX ix_fato_faturamento_unidade_negocio_id ON dw.fato_faturamento(unidade_negocio_id);

CREATE INDEX ix_fato_faturamento_tipo_contrato_id ON dw.fato_faturamento(tipo_contrato_id);

CREATE TABLE dw.fato_custos_despesas (
  row_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_lancamento text NOT NULL CHECK(length(id_lancamento) BETWEEN 1 AND 200),
  data_id integer NOT NULL REFERENCES dw.dim_tempo(data_id),
  categoria_id bigint NOT NULL REFERENCES dw.dim_categoria(categoria_id),
  tipo_despesa_id bigint NOT NULL REFERENCES dw.dim_tipo_despesa(tipo_despesa_id),
  centro_custo_id bigint NOT NULL REFERENCES dw.dim_centro_custo(centro_custo_id),
  valor numeric(18,2) NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE (id_lancamento)
);

CREATE INDEX ix_fato_custos_despesas_batch ON dw.fato_custos_despesas(batch_id);

CREATE INDEX ix_fato_custos_despesas_data_id ON dw.fato_custos_despesas(data_id);

CREATE INDEX ix_fato_custos_despesas_categoria_id ON dw.fato_custos_despesas(categoria_id);

CREATE INDEX ix_fato_custos_despesas_tipo_despesa_id ON dw.fato_custos_despesas(tipo_despesa_id);

CREATE INDEX ix_fato_custos_despesas_centro_custo_id ON dw.fato_custos_despesas(centro_custo_id);

CREATE TABLE dw.fato_orcamento (
  row_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  data_id integer NOT NULL REFERENCES dw.dim_tempo(data_id),
  tipo_orcamento_id bigint NOT NULL REFERENCES dw.dim_tipo_orcamento(tipo_orcamento_id),
  unidade_negocio_id bigint NOT NULL REFERENCES dw.dim_unidade_negocio(unidade_negocio_id),
  valor_orcado numeric(18,2) NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE (data_id, tipo_orcamento_id, unidade_negocio_id)
);

CREATE INDEX ix_fato_orcamento_batch ON dw.fato_orcamento(batch_id);

CREATE INDEX ix_fato_orcamento_data_id ON dw.fato_orcamento(data_id);

CREATE INDEX ix_fato_orcamento_tipo_orcamento_id ON dw.fato_orcamento(tipo_orcamento_id);

CREATE INDEX ix_fato_orcamento_unidade_negocio_id ON dw.fato_orcamento(unidade_negocio_id);

CREATE TABLE dw.fato_contas_receber (
  row_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_titulo text NOT NULL CHECK(length(id_titulo) BETWEEN 1 AND 200),
  cliente_id bigint NOT NULL REFERENCES dw.dim_cliente(cliente_id),
  data_emissao_id integer NOT NULL REFERENCES dw.dim_tempo(data_id),
  data_vencimento_id integer NOT NULL REFERENCES dw.dim_tempo(data_id),
  status_id bigint NOT NULL REFERENCES dw.dim_status(status_id),
  valor numeric(18,2) NOT NULL,
  dias_atraso integer NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE (id_titulo),
  CHECK(dias_atraso >= 0)
);

CREATE INDEX ix_fato_contas_receber_batch ON dw.fato_contas_receber(batch_id);

CREATE INDEX ix_fato_contas_receber_cliente_id ON dw.fato_contas_receber(cliente_id);

CREATE INDEX ix_fato_contas_receber_data_emissao_id ON dw.fato_contas_receber(data_emissao_id);

CREATE INDEX ix_fato_contas_receber_data_vencimento_id ON dw.fato_contas_receber(data_vencimento_id);

CREATE INDEX ix_fato_contas_receber_status_id ON dw.fato_contas_receber(status_id);

CREATE TABLE dw.fato_metas_negocio (
  row_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  data_id integer NOT NULL REFERENCES dw.dim_tempo(data_id),
  unidade_negocio_id bigint NOT NULL REFERENCES dw.dim_unidade_negocio(unidade_negocio_id),
  margem_meta numeric(18,4) NOT NULL,
  crescimento_meta numeric(18,4) NOT NULL,
  ticket_medio_meta numeric(18,2) NOT NULL,
  batch_id uuid NOT NULL REFERENCES dw.etl_batch(batch_id),
  tempo_carga timestamptz NOT NULL,
  UNIQUE (data_id, unidade_negocio_id),
  CHECK(margem_meta BETWEEN -1 AND 1 AND crescimento_meta >= -1 AND ticket_medio_meta >= 0)
);

CREATE INDEX ix_fato_metas_negocio_batch ON dw.fato_metas_negocio(batch_id);

CREATE INDEX ix_fato_metas_negocio_data_id ON dw.fato_metas_negocio(data_id);

CREATE INDEX ix_fato_metas_negocio_unidade_negocio_id ON dw.fato_metas_negocio(unidade_negocio_id);

CREATE VIEW dw.vw_faturamento_mensal AS
SELECT date_trunc('month', d.data)::date AS competencia, u.unidade_negocio,
 SUM(f.receita_bruta) AS receita_bruta, SUM(f.impostos) AS impostos, SUM(f.receita_liquida) AS receita_liquida
FROM dw.fato_faturamento f JOIN dw.dim_tempo d USING(data_id)
JOIN dw.dim_unidade_negocio u USING(unidade_negocio_id) GROUP BY 1, 2;

CREATE VIEW dw.vw_custos_mensais AS
SELECT date_trunc('month', d.data)::date AS competencia, c.categoria, SUM(f.valor) AS valor
FROM dw.fato_custos_despesas f JOIN dw.dim_tempo d USING(data_id)
JOIN dw.dim_categoria c USING(categoria_id) GROUP BY 1, 2;

CREATE VIEW dw.vw_contas_receber_status AS
SELECT s.status, count(*) AS titulos, SUM(f.valor) AS valor
FROM dw.fato_contas_receber f JOIN dw.dim_status s USING(status_id) GROUP BY 1;
