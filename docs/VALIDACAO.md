# Resultado da profissionalização — validação local

Data: 20/10/2026.
Base original: main em `df5c4cdf7230b777b72c6e03ae3cf4b327337ce8`.
Estado: entrega em branch separada para revisão, ainda não integrada à main.
O histórico não foi reescrito. As evidências abaixo registram a validação local.

## Resultados executados

**55 testes aprovados em cada uma de duas instalações novas**, sem falhas,
erros ou testes ignorados. Ambiente: Windows x86-64, Python 3.12.14,
PostgreSQL 18.6 real e descartável.

| Execução | Instalação | Testes | Falhas/erros/ignorados | Demonstração | Servidor |
| --- | --- | --- | --- | --- | --- |
| 1 | requirements.txt, ambiente vazio | 55 | 0 / 0 / 0 | Concluída | Encerrado |
| 2 | requirements-lock.txt, outro ambiente vazio | 55 | 0 / 0 / 0 | Concluída | Encerrado |

As duas instalações passaram em `pip check` e têm as mesmas versões resolvidas.
Tempos da suíte: 68.063s e 73.636s, respectivamente. São tempos observados nos
testes locais, não benchmark do ETL em produção.

Resultado estruturado: [evidence/validacao_local.json](evidence/validacao_local.json).

## Cobertura significativa

**30 testes de contrato/configuração:** precisão monetária, não finitos, datas,
IDs textuais, nomes, chaves duplicadas, colunas e abas, nulos, metas, receita
líquida, Excel e hash, configuração segura, importação sem carga e erros da CLI.

**25 testes PostgreSQL:** DDL, PK/UNIQUE/FK, precisão NUMERIC, preservação de
lançamentos, correção de valores e dimensões, títulos com atributos mutáveis,
metas por competência, política de ausência, rollback, reconciliação, lock,
recusa de schema legado/divergente, views, ledger e fluxo Excel/CLI/demo.

Os cenários de rollback provocam falhas reais no banco e divergências controladas.
Asserções conferem preservação de staging, fatos e ledger anteriores. Há teste
de reconciliação que verifica também rollback das novas dimensões.

## Alterações realizadas

- Credencial e caminho pessoal removidos da versão de trabalho; configuração
  em `src/config.py`, `.env.example` e exclusões de arquivos locais no Git.
- ETL protegido por `main`, com CLI explícita e sem I/O na importação.
- Contrato aprovado implementado em `src/contracts.py` e `src/model.py`:
  IDs estáveis, grãos explícitos, datas estritas, Decimal e validação de duplicatas.
- DDL versionado para cinco staging, nove dimensões, cinco fatos, controle de
  versão, ledger de lotes e três views. Nenhum DROP/CASCADE de objetos do usuário.
- Carga em uma transação com lock, UPSERT e reconciliação de contagens/medidas.
- Demo fictícia, execução de testes e script de PostgreSQL temporário.
- Dependências revisadas, fixadas e instaladas em dois ambientes novos.
- Workflow de GitHub Actions preparado e validado por actionlint 1.7.12
  (sem ShellCheck/pyflakes); ainda sem execução remota nesta entrega.
- README, contrato, modelagem, reprodução e segurança reescritos conforme evidências.

O diagrama PNG original é preservado como legado; o diagrama mantido da versão
nova está em [MODELAGEM.md](MODELAGEM.md), em conjunto com o DDL.

## Compatibilidade e decisões aprovadas

Não há conversão automática de um Excel antigo sem IDs para o contrato novo.
Não se inferem IDs por posição, somas, cliente ou atributos mutáveis.
Orçamento requer `Unidade_Negocio` e metas requerem competência.
IDs e nomes naturais são demonstrativos, não cadastro mestre empresarial.

O DW conserva fatos ausentes da próxima origem. O ledger guarda métricas de
lotes completos, sem versões das linhas-fonte e sem histórico completo de auditoria.
Essas escolhas estão detalhadas em [CONTRATO_DADOS.md](CONTRATO_DADOS.md).

## Limitações e pendências

1. Publicar a branch e abrir proposta somente após autorização do usuário.
2. Acompanhar a primeira execução real no GitHub/Linux. Actionlint não substitui CI.
3. Integrar à main somente após aprovação específica e testes remotos satisfatórios.
4. Credenciais continuam no histórico original. Não foi feita rotação, revogação,
   reescrita de histórico ou remoção de caches. Isso exige ação separada autorizada.
5. Nenhum sistema, arquivo ou banco corporativo foi acessado. Não há homologação
   de dados reais, migração de DW produtivo, benchmark de escala ou teste macOS.
6. Não há dashboard Power BI, medidas DAX, EBITDA validado ou modelo preditivo.
7. O workflow não configura proteção de branch nem obrigação de check para merge.
8. O cluster e a demo usam privilégios de teste; o roteiro não implanta papéis,
   backup, monitoramento ou permissões de produção.

## Prontidão

A implementação local demonstrou os comportamentos centrais de confiabilidade e
reprodução propostos. Está pronta para revisão e publicação autorizada da proposta.
O ciclo ainda depende da publicação e validação remota; não declarar essa parte
concluída antes de observar o resultado no GitHub.
