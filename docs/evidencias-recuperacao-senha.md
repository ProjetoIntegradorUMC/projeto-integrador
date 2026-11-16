## 1. Solicitação de recuperação de senha

### Passo a passo

1. Acessar a tela de login pelo frontend.
2. Selecionar a opção **"Esqueci minha senha"**.
3. Informar o e-mail cadastrado.
4. Solicitar a recuperação de senha.
5. Verificar a mensagem apresentada pelo sistema.

![Solicitação de recuperação de senha](img/11-recuperacao-senha.png)

## 2. Recebimento do link de recuperação

### Passo a passo

1. Acessar a caixa de entrada do e-mail utilizado na solicitação.
2. Localizar o e-mail de recuperação de senha.
3. Verificar o recebimento do link de recuperação.
4. Acessar o link recebido.
5. Verificar o direcionamento para a tela de redefinição de senha.

![E-mail de recuperação recebido](img/12-email-recuperacao.png)

## 3. Redefinição de senha com token válido

### Passo a passo

1. Acessar a tela de redefinição por meio do link recebido.
2. Informar uma nova senha.
3. Confirmar a nova senha.
4. Confirmar a redefinição.
5. Verificar a mensagem de sucesso apresentada pelo sistema.

![Redefinição de senha](img/13-redefinicao-senha.png)

![Senha redefinida com sucesso](img/14-senha-redefinida.png)

## 4. Login com a nova senha

### Passo a passo

1. Retornar à tela de login.
2. Informar o usuário/e-mail cadastrado.
3. Informar a nova senha definida durante a recuperação.
4. Clicar no botão de login.
5. Verificar que as novas credenciais foram aceitas pelo sistema.
6. Confirmar o acesso à conta.

![Login com a nova senha](img/15-login-nova-senha.png)

## 5. Token expirado

### Passo a passo

1. Solicitar um novo link de recuperação pelo frontend.
2. Receber o link de recuperação por e-mail.
3. Aguardar o período de validade configurado para o token.
4. Acessar o link após o período de validade.
5. Informar uma nova senha.
6. Tentar confirmar a redefinição.
7. Verificar que a tentativa foi rejeitada pelo sistema.

![Email expirado](img/email-token-expirado.png)
![Token expirado](img/16-token-expirado.png)

## 6. Tentativa de reutilização do token

### Passo a passo

1. Solicitar um novo link de recuperação pelo frontend.
2. Acessar o link recebido por e-mail.
3. Redefinir a senha utilizando o token válido.
4. Confirmar que a redefinição foi realizada com sucesso.
5. Acessar novamente o mesmo link utilizado anteriormente.
6. Tentar redefinir a senha novamente.
7. Verificar que a tentativa de reutilização foi rejeitada pelo sistema.

![Token reutilizado](img/17-token-reutilizado.png)

## Validação pelo frontend

Todos os passos deste roteiro são executados exclusivamente pela interface
do frontend, incluindo a solicitação de recuperação, acesso ao link,
redefinição da senha, login com a nova senha e as tentativas com tokens
expirados ou já utilizados.

## 7. Entrega SMTP em produção (`https://mentory.stack-n8n.cloud`)

### Passo a passo

1. Acessar o ambiente de produção em `https://mentory.stack-n8n.cloud`.
2. Solicitar a recuperação de senha via `POST /auth/forgot-password` para um endereço de e-mail cadastrado.
3. Confirmar o disparo SMTP autenticado a partir do remetente `projetomentory@gmail.com` contendo o assunto de redefinição e o link único com validade de 15 minutos.

![E-mail de recuperação recebido](img/31-email-recuperacao.png)

## 8. Uniformidade de resposta e proteção contra enumeração de contas

Para impedir que atacantes identifiquem quais endereços de e-mail possuem cadastro ativo na plataforma, o endpoint `POST /auth/forgot-password` devolve o mesmo código HTTP, mensagem genérica e comportamento temporal tanto para e-mails cadastrados quanto para e-mails inexistentes.

### 8.1. Validação operacional em produção (`curl`)

Comparação direta do código de status HTTP retornado pelo ambiente de produção (`https://mentory.stack-n8n.cloud/auth/forgot-password`) para e-mail cadastrado e e-mail inexistente:

```bash
$ curl -s -o /dev/null -w "%{http_code}\n" -X POST https://mentory.stack-n8n.cloud/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "<email-cadastrado>"}'
200

$ curl -s -o /dev/null -w "%{http_code}\n" -X POST https://mentory.stack-n8n.cloud/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "nao-existe@exemplo.invalid"}'
200
```

Na sequência de requisições consecutivas pelo mesmo IP, ambos os cenários também receberam tratamento uniforme do controle de *rate limiting* (código HTTP, corpo JSON e latência equivalente):

```text
--- E-mail cadastrado ---
{"error":"Muitas tentativas. Tente novamente em 11 minuto(s)."}
HTTP_CODE: 429 | TIME_TOTAL: 0.086648s

--- E-mail não cadastrado ---
{"error":"Muitas tentativas. Tente novamente em 11 minuto(s)."}
HTTP_CODE: 429 | TIME_TOTAL: 0.067152s
```

### 8.2. Cobertura automatizada (`tests/test_account_enumeration.py`)

A proteção contra enumeração de contas no fluxo de recuperação de senha também é verificada de forma automatizada na suíte de testes em `tests/test_account_enumeration.py`, que valida que `POST /auth/forgot-password` retorna exatamente o mesmo código HTTP e o mesmo payload JSON para e-mails existentes e inexistentes (função `test_forgot_password_retorna_mesma_resposta_para_email_existente_e_inexistente`), além de cobrir anti-enumeração e mitigação de *timing attack* no login e no cadastro.