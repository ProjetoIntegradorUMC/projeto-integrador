# Configuração de variáveis de ambiente

O Mentory utiliza variáveis de ambiente para separar configurações
operacionais e segredos do código-fonte. O arquivo `.env.example` apresenta
as variáveis esperadas, mas os valores reais devem ser definidos apenas no
arquivo `.env`, que não deve ser versionado.

## Banco de dados

### `DB_HOST`

Informa o endereço do servidor PostgreSQL. Em uma execução local, pode ser
`localhost`. Essa variável permite que a aplicação encontre o banco sem
fixar o endereço no código.

### `DB_PORT`

Informa a porta usada pelo PostgreSQL. O valor também é usado pelo Docker
Compose para publicar a porta do container. A configuração precisa ser
compatível com a porta efetivamente disponível no ambiente.

### `DB_NAME`

Define o nome do banco de dados usado pelo PostgreSQL e pela aplicação.
Manter esse valor na configuração evita que o nome do banco fique acoplado
ao código e permite utilizar bancos diferentes em cada ambiente.

### `DB_ADMIN_USER` e `DB_ADMIN_PASSWORD`

Identificam as credenciais administrativas usadas na criação do banco e na
execução dos scripts de configuração de roles e permissões. Essas
credenciais não devem ser usadas pela aplicação durante a execução normal,
porque possuem privilégios maiores que os necessários para as requisições.

### `DB_APP_USER` e `DB_APP_PASSWORD`

Identificam o usuário dedicado usado pelo backend para acessar o banco. O
uso de uma conta separada limita o impacto de um comprometimento da
aplicação e permite aplicar permissões específicas, incluindo a proteção
append-only dos logs de auditoria.

### `DB_APP_ROLE`

Informa o nome do role associado ao usuário da aplicação. Os scripts em
`backend/db` usam esse valor para configurar permissões no PostgreSQL sem
exigir que o nome do role esteja escrito no código ou nos scripts.

## Segredos da aplicação

### `SECRET_KEY`

É a chave usada pelo Flask para assinar os dados de sessão. Ela protege
informações do fluxo de autenticação, incluindo o login pendente durante a
validação do 2FA. A chave deve ser aleatória, longa e mantida em segredo,
pois uma pessoa que a obtenha pode tentar forjar dados de sessão.

Essa variável é obrigatória. A aplicação não deve iniciar sem ela e não
possui fallback hardcoded.

### `TOTP_ENCRYPTION_KEY`

É a chave Fernet usada para cifrar o segredo TOTP antes que ele seja
armazenado na coluna `two_factor_secret`. O segredo TOTP permite gerar e
validar códigos do segundo fator, portanto não deve ficar legível no banco
de dados.

Essa chave é separada da `SECRET_KEY` para manter responsabilidades
criptográficas independentes. Ela também é obrigatória e precisa ser uma
chave Fernet válida. Pode ser gerada com:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Não altere essa chave enquanto houver segredos TOTP cifrados no banco. A
troca sem um procedimento de recriptografia impede a validação do 2FA dos
usuários existentes.

## Serviço de e-mail

### `MAIL_SERVER`

Define o endereço do servidor SMTP usado no envio de mensagens, como os
e-mails de recuperação de senha. O código utiliza `smtp.gmail.com` como
valor padrão quando a variável não é informada.

### `MAIL_PORT`

Define a porta do servidor SMTP. O valor padrão é `587`, normalmente usado
com STARTTLS. A porta precisa corresponder à configuração do servidor de
e-mail escolhido.

### `MAIL_USERNAME`

Define a conta usada para autenticar no servidor SMTP e também o endereço
usado no campo remetente das mensagens. Deve ser configurada junto com
`MAIL_PASSWORD`.

### `MAIL_PASSWORD`

Define a credencial da conta SMTP. Ela é necessária para o envio de
mensagens e deve ser tratada como segredo. Quando o provedor exigir, use
uma senha de aplicativo em vez da senha principal da conta.

## Administração e aplicação

### `ADMIN_EMAIL`

Define o endereço de e-mail autorizado a acessar o painel de auditoria.
Esse controle evita adicionar um campo de privilégio administrativo ao
modelo de usuário e restringe a visualização dos logs de segurança.

### `APP_BASE_URL`

Define o endereço público da aplicação usado na criação dos links de
recuperação de senha enviados por e-mail. Em desenvolvimento, o valor
normalmente é `http://localhost:5000`. Em outro ambiente, deve apontar para
o endereço que os usuários realmente conseguem acessar.

Se a variável não for informada, o backend usa
`http://localhost:5000` como padrão.

## Exemplo de configuração

Depois de copiar o arquivo de exemplo, preencha os valores no `.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mentory
DB_ADMIN_USER=postgres
DB_ADMIN_PASSWORD=senha-administrativa
DB_APP_USER=mentory_app
DB_APP_PASSWORD=senha-da-aplicacao
DB_APP_ROLE=mentory_app_role

SECRET_KEY=valor-aleatorio-gerado
TOTP_ENCRYPTION_KEY=chave-fernet-gerada

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=conta@example.com
MAIL_PASSWORD=senha-de-aplicativo

ADMIN_EMAIL=administrador@example.com
APP_BASE_URL=http://localhost:5000
```

Os valores exibidos são apenas ilustrativos. Não copie senhas ou chaves de
exemplo para um ambiente real.
