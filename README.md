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

---

##  Documentação

- **[Ler a Documentação Técnica de Autenticação e Sessão ](docs/autenticacao.md)**
- **[Ler a Documentação Técnica de Recuperação de Senha ](docs/recuperacao-senha.md)**
- **[Ler a Análise de Riscos e Ameaças ](docs/analise-riscos.md)**
- **[Ler a Documentação Técnica de Conformidade LGPD ](docs/lgpd.md)**
- **[Ler a Documentação de Imutabilidade dos Logs de Auditoria ](docs/logs-imutaveis.md)**
- **[Ler a Documentação Técnica do Painel de Auditoria ](docs/auditoria-logs.md)**

---

## 🚀 Como Executar o Projeto Localmente

O projeto utiliza o Docker para orquestrar o banco de dados de forma simplificada.

### Pré-requisitos
- [Docker](https://www.docker.com/) e Docker Compose
- [Python 3.13](https://www.python.org/)

### Passo a Passo

1. **Suba o Banco de Dados:**
   ```bash
   docker-compose up -d postgres
   ```
2. **Configure as credenciais no `.env`:**
   - `DB_ADMIN_USER` e `DB_ADMIN_PASSWORD` são usados pelo PostgreSQL e pelos scripts administrativos.
   - `DB_APP_USER` e `DB_APP_PASSWORD` são usados pela aplicação.
   - `DB_APP_ROLE` identifica o role de permissões da aplicação.

   Execute `backend/db/app_role_setup.sql` e `backend/db/log_permissions.sql` com o usuário administrador antes de iniciar a aplicação com o usuário dedicado. Os detalhes estão em [Proteção contra alteração dos logs](docs/logs-imutaveis.md).
3. **Configure o Ambiente Virtual:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Inicie o Servidor:**
   ```bash
   python run.py
   ```
5. **Acesse no Navegador:**
   Abra `http://127.0.0.1:5000`

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
