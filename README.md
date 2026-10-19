# 🎓 Mentory - Plataforma de Monitoria Acadêmica

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)

**Mentory** é um sistema que conecta alunos que dominam uma disciplina (monitores) com alunos que precisam de ajuda (mentorados), dentro da própria instituição de ensino. Este projeto está sendo desenvolvido como parte do **Projeto Integrador (UMC)**.

---

## 🎯 Por que o Mentory? (Diferencial e Escalabilidade)

- **Problema Real:** Ataca a dificuldade de acompanhamento em disciplinas específicas, o que está diretamente ligado à evasão escolar. Não é apenas um cadastro genérico.
- **Controle de Acesso:** Possui uma estrutura natural de papéis (aluno-monitor, aluno-mentorado, coordenação), o que exige um robusto sistema de permissões e segurança da informação.
- **Proteção de Dados:** Lida com dados acadêmicos e de desempenho (dados pessoais sensíveis), conversando diretamente com a **LGPD**.

---

## 🔒 Entrega Atual: Módulo de Autenticação e Segurança

Nesta fase inicial do projeto, implementamos a fundação de segurança do Mentory:
- Autenticação com senhas protegidas via hash adaptativo (`bcrypt`).
- **Gestão de Sessão (Stateful)** armazenada no banco para revogação imediata (LGPD Art. 18).
- **Proteção contra Força Bruta** (Time-Lock de 15 minutos).
- **Autenticação de Dois Fatores (2FA)** via TOTP.
- **Mitigação de Enumeração de Contas e Timing Attacks** (respostas genéricas uniformizadas e equalização de latência criptográfica).

---

##  Documentação

- **[Visão geral e arquitetura do sistema](docs/visao-geral.md)**: ponto de entrada da documentação técnica
- **[Ler a Documentação Técnica de Autenticação e Sessão ](docs/autenticacao.md)**
- **[Ler a Documentação Técnica de Criptografia e Comunicação Segura ](docs/criptografia.md)**
- **[Ler a Documentação Técnica de Recuperação de Senha ](docs/recuperacao-senha.md)**
- **[Ler a Análise de Riscos e Ameaças ](docs/analise-riscos.md)**
- **[Ler a Documentação Técnica de Conformidade LGPD ](docs/lgpd.md)**
- **[Ler a Documentação de Imutabilidade dos Logs de Auditoria ](docs/logs-imutaveis.md)**
- **[Ler a Documentação Técnica do Painel de Auditoria ](docs/auditoria-logs.md)**
- **[Ler a documentação das variáveis de ambiente](docs/configuracao-ambiente.md)**
- **[Ler a Documentação de Segurança no Pipeline de CI/CD](docs/pipeline-seguranca.md)**
- **[Ler a documentação de Rate Limiting](docs/rate-limiting.md)**
- **[Validação dos requisitos do checklist](docs/validacao-requisitos.md)**: mapeamento completo dos itens às evidências do repositório
- **[Ler o Guia de Deploy em Produção na VPS (Traefik + CD)](docs/deploy-vps.md)**

---

## 🚀 Como Executar o Projeto Localmente

O projeto utiliza o Docker para orquestrar o banco de dados de forma simplificada.

### Pré-requisitos
- [Docker](https://www.docker.com/) e Docker Compose
- [Python 3.13](https://www.python.org/)

### Passo a Passo

1. **Configure as credenciais no `.env`:**
   - `DB_ADMIN_USER` e `DB_ADMIN_PASSWORD` são usados pelo PostgreSQL e pelos scripts administrativos.
   - `DB_APP_USER` e `DB_APP_PASSWORD` são usados pela aplicação.
   - `DB_APP_ROLE` identifica o role de permissões da aplicação.
   - Gere cada senha com `python -c "import secrets; print(secrets.token_urlsafe(32))"` e use senhas **diferentes** para o administrador e para a aplicação. Nunca faça commit do `.env`.
   - O backend conecta com `DB_APP_USER` (privilégios limitados). `DB_ADMIN_*` é usado só pelo container do PostgreSQL e por scripts administrativos.
   - O `docker-compose.yml` publica o PostgreSQL apenas em `127.0.0.1`: só o seu computador acessa o banco. Para acessar de outra máquina, use um túnel SSH (`ssh -L 5432:127.0.0.1:5432 usuario@servidor`) ou VPN, em vez de abrir a porta para a rede.
   - Se o banco já existia, mudar a senha no `.env` não altera a senha dentro do PostgreSQL. Troque-a com `\password <usuario>` no `psql` (`docker exec -it projeto-integrador-postgres psql -U <DB_ADMIN_USER> -d <DB_NAME>`) ou recrie o volume com `docker compose down -v` (apaga os dados).
   - `SECRET_KEY` protege as sessões Flask e `TOTP_ENCRYPTION_KEY` cifra os
     segredos do 2FA; ambas são obrigatórias e devem ser geradas fora do código.

   Copie `.env.example` para `.env` e preencha as variáveis de banco, e-mail e
   aplicação. Gere as chaves de segurança com o ambiente virtual ativado:

   ```bash
   python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
   python -c "from cryptography.fernet import Fernet; print('TOTP_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
   ```

   Adicione os valores exibidos nas respectivas variáveis do arquivo `.env`.
   A aplicação recusará iniciar se `SECRET_KEY` ou `TOTP_ENCRYPTION_KEY`
   estiver ausente ou inválida. Mantenha essas chaves em segredo e não as
   versione no repositório.

2. **Configure e inicie todo o ambiente:**
   ```bash
   bash setup.sh
   ```
   O script cria o ambiente virtual, instala as dependências, sobe o
   PostgreSQL, cria as entidades usando os models, valida os identificadores e
   aplica os privilégios mínimos no banco, gera automaticamente os certificados
   TLS locais (`cert.pem` e `key.pem` via `gerar_certificados.sh`) caso
   `SECURE_COOKIES=true` esteja ativo no `.env`, e inicia o backend. Não é
   necessário executar a aplicação previamente nem rodar comandos SQL
   manualmente.

3. **Acesse no Navegador:**
   - Com `SECURE_COOKIES=true` (padrão recomendado no `.env.example`, com `cert.pem` e `key.pem` gerados): abra `https://127.0.0.1:5000` (aceite o aviso de certificado autoassinado no navegador).
   - Caso opte por rodar apenas em HTTP local sem certificados TLS, defina `SECURE_COOKIES=false` no `.env`, remova `cert.pem`/`key.pem` se existirem e acesse `http://127.0.0.1:5000`.

Para interromper o backend, use `Ctrl+C`. O PostgreSQL permanece no Docker e
pode ser parado com `docker compose stop postgres`.

---

## 🧪 Testes Automatizados

Os testes usam um banco separado do de desenvolvimento (`projeto_integrador_test`), para que o `drop_all()` dos testes nunca toque nos dados reais.

1. **Crie o banco de testes (uma vez), com o container do Postgres rodando:**
```bash
set -a
source .env
set +a

docker exec -e PGPASSWORD="$DB_ADMIN_PASSWORD" projeto-integrador-postgres \
   psql -v ON_ERROR_STOP=1 -U "$DB_ADMIN_USER" -d "$DB_NAME" \
   -c "CREATE DATABASE projeto_integrador_test OWNER \"$DB_APP_USER\";"
```
2. **Instale as dependências de desenvolvimento e rode os testes**, com o ambiente virtual ativado:
```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

Não aplique o `log_permissions.sql` no banco de testes: os testes recriam as tabelas a cada execução, e o usuário da aplicação precisa ser dono delas.

---

## 📦 Release

O workflow em `.github/workflows/release.yml` cria uma release ao enviar uma tag no formato `v*`.

Fluxo:

```bash
# abrir PR e mergear na main

git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Importante:

- não faça commit direto na `main`;
- a tag precisa começar com `v` (ex.: `v1.2.3`);
- o workflow gera o ZIP da aplicação e cria a release no GitHub automaticamente.

---
*Desenvolvido pela equipe do Projeto Integrador - UMC.*
