# Evidências de testes LGPD ponta a ponta

Este documento registra a execução do roteiro da issue #29. O teste utiliza somente dados sintéticos e reproduz as operações
disponibilizadas pela interface do frontend.

## Execução

- **Data:** 13/09/2026
- **Ambiente:** aplicação local em `http://127.0.0.1:5000`
- **Dados utilizados:** dois usuários temporários (`Titular A` e
  `Titular B`), com e-mails `@example.test`
- **Persistência:** PostgreSQL local iniciado pelo `docker compose`
- **Resultado geral:** `E2E_LGPD_RESULT=PASS`
- **Limpeza:** as duas contas criadas durante o teste foram excluídas ao final

## Roteiro executado e evidências observadas

### 1. Cadastro e consentimento

1. A página inicial foi carregada com status HTTP `200`.
2. A interface apresentou a opção **Meus dados**.
3. O Usuário A foi cadastrado com nome, usuário, e-mail, senha e
   `consent_given=true`.
4. O Usuário B foi cadastrado com os mesmos campos e consentimento.

**Evidência textual:** os dois cadastros retornaram HTTP `201`. O fluxo não
prosseguiu sem o aceite de consentimento porque o campo é obrigatório no
frontend.

### 2. Oferta de monitoria

1. O Usuário A realizou login.
2. O Usuário A publicou uma monitoria de Matemática com uma descrição.
3. A monitoria foi consultada pelo fluxo de monitorias disponíveis.

**Evidência textual:** login retornou HTTP `200` e publicação retornou HTTP
`201`.

### 3. Inscrição por outro usuário

1. O Usuário B realizou login.
2. O Usuário B consultou as monitorias disponíveis.
3. O Usuário B se inscreveu na oferta criada pelo Usuário A.

**Evidência textual:** consulta retornou HTTP `200`, a oferta foi localizada e
a inscrição retornou HTTP `201`. A oferta apareceu na consulta de dados do
Usuário B como inscrição em monitoria.

### 4. Consulta dos dados pessoais

1. O Usuário A consultou seus dados pela operação usada pela tela **Meus
   dados**.
2. O Usuário B repetiu a consulta após realizar a inscrição.
3. A resposta foi validada para conter as seções:
   - **Dados pessoais**
   - **Monitorias oferecidas**
   - **Inscrições em monitorias**

**Evidência textual:** as duas consultas retornaram HTTP `200`; a exportação do
Usuário A continha as três seções e a do Usuário B continha a inscrição
realizada.

### 5. Exportação

O conteúdo retornado pela operação de exportação foi validado como JSON
estruturado e compatível com o que a interface baixa como
`meus_dados_lgpd.json`.

**Evidência textual:** a exportação retornou HTTP `200` para os dois usuários,
contendo dados pessoais, monitorias e inscrições. O fluxo não expõe senha,
hash de senha, segredo de 2FA ou token de sessão.

### 6. Revogação, exclusão e tentativa posterior de acesso

1. O Usuário B excluiu a conta pela ação de exclusão disponível em **Meus
   dados**.
2. A sessão do Usuário B foi consultada imediatamente após a exclusão.
3. Foi realizada uma nova tentativa de login com as mesmas credenciais.
4. O Usuário A também foi excluído para limpar os dados temporários do teste.

**Evidência textual:** a exclusão do Usuário B retornou HTTP `200`; a consulta
da sessão após a exclusão retornou HTTP `401`; o novo login retornou HTTP
`401`. A exclusão do Usuário A também retornou HTTP `200`.

## Resultado de aceite

| Critério                                                                              | Resultado     |
| ------------------------------------------------------------------------------------- | ------------- |
| Roteiro cobrindo consentimento, monitoria, inscrição, consulta, exportação e exclusão | PASS          |
| Evidências organizadas em um único local                                              | PASS          |
| Cenários reproduzíveis pelo fluxo do frontend                                         | PASS          |
| Vídeo ou prints                                                                       | Não aplicável |
