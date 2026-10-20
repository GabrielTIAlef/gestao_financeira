# Configuração e exposição histórica

A versão anterior incluía uma senha PostgreSQL literal e um caminho pessoal.
Foram encontrados cinco commits com atribuição literal de senha na revisão
direcionada de 12 commits. Valores não são reproduzidos aqui. Essa inspeção não
garante ausência de outros segredos em todas as cópias e referências.

Corrigir o código atual não revoga credenciais nem remove versões anteriores.
O responsável autorizado deve tratar credenciais publicadas como expostas, sem
testá-las. Contas da antiga empresa devem ser tratadas pelos administradores dela;
não acessar, alterar ou reutilizar essas contas por iniciativa própria.

O histórico não foi reescrito nesta entrega. Reescrita, coordenação de clones e
eventual remoção de caches/referências no GitHub exigem ação separada e autorização.
Não compartilhar clones ou backups do estado anterior, que podem conter segredos.

## Configuração local

- Use apenas contas e bancos sob sua autorização. Prefira a demo fictícia.
- `.env.example` documenta variáveis; `.env` local não é versionado.
- A CLI não assume senha, usuário administrativo ou banco de uma instalação antiga.
- Configure uma conta própria da aplicação. `--init` precisa criar schemas e
  objetos em um banco novo, não de privilégio de superusuário.
- Para operação separada, o administrador pode conceder ao papel da aplicação
  USAGE nos schemas, SELECT/INSERT/UPDATE/DELETE nas tabelas necessárias e USAGE
  nas sequences. Inicialização e migrações ficam com o proprietário do schema.
- O SQL versionado não cria papéis, usuários, senhas ou bancos.
- Caminhos relativos são resolvidos a partir da raiz do projeto.
- O ETL não usa APIs corporativas, navegador ou integrações da antiga empresa.
- Logs e erros não incluem URLs de conexão, valores das linhas ou senha do driver.

## Artefatos e testes

Não publique planilhas reais, `.env`, exportações, logs, dumps e diretórios de
bancos temporários. O `.gitignore` reduz erros acidentais, mas não substitui revisão
do que foi adicionado ao Git. Saídas reais podem conter informações financeiras
e cadastrais mesmo quando não contêm credenciais.

O script de validação inicia um PostgreSQL restrito à interface local com a conta
fictícia `finance_test` e autenticação trust. Os bancos são exclusivos dos testes
e removidos por nome gerado. Essa configuração não é uma instalação de produção.

Os testes com marcação explícita criam e apagam bancos locais; nunca forneça uma
URL de produção em `FINANCE_TEST_PG_ADMIN_URL`. A demo aceita somente banco local
`finance_demo` ou `finance_demo_*` e rejeita parâmetros de redirecionamento na URL.
Contas e nomes de banco são guardas contra acidentes, não uma fronteira contra
alguém que altere o código ou configure deliberadamente um proxy local.
