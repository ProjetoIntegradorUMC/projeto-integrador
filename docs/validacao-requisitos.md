# Validação dos requisitos

Este documento relaciona cada item do checklist de `docs/Requisitos.pdf` ao
artefato do repositório que demonstra sua implementação, documentação ou
validação. Os caminhos são relativos à raiz do projeto.

## 1. Autenticação e Gestão de Credenciais

| Nº | Requisito | Evidência no repositório |
|---|---|---|
| 1.1 | Uso de hash criptográfico seguro para senhas (Argon2, bcrypt ou PBKDF2) | `backend/app/routes/auth.py`: cadastro e redefinição usam `bcrypt.hashpw`; `docs/autenticacao.md`, seção “Gestão de credenciais e criptografia”. |
| 1.2 | Parâmetros de custo do hash configurados e justificados | `backend/app/routes/auth.py`: uso de `bcrypt.gensalt(rounds=12)`; `docs/autenticacao.md`, seção “Gestão de credenciais e criptografia”, justifica o custo. |
| 1.3 | Uso de salt criptográfico único por usuário | `bcrypt.gensalt()` gera salt aleatório a cada hash em `backend/app/routes/auth.py`; o resultado também é descrito em `docs/dados-pessoais.md`. |
| 1.4 | Armazenamento correto do hash + salt | Campo `User.password_hash` em `backend/app/models.py`; o hash bcrypt autocontido é persistido, sem senha em texto puro, conforme `docs/autenticacao.md`. |
| 1.5 | Autenticação de dois fatores (2FA) implementada | `backend/app/two_factor.py` implementa TOTP; rotas de ativação, confirmação e desativação estão em `backend/app/routes/auth.py`; fluxo visual em `docs/img/3-2FA.png`. |
| 1.6 | Validação do 2FA após autenticação primária | `backend/app/routes/auth.py`: login cria o estado intermediário e exige `/auth/verify-2fa` antes de criar a sessão final; `frontend/index.html`, seção “2FA VERIFICATION”. |
| 1.7 | Fluxo de autenticação documentado | `docs/autenticacao.md`, seções “Visão Geral”, “Como o token de sessão é armazenado” e “Diagrama de Fluxo”; `docs/visao-geral.md`, módulo de autenticação. |
| 1.8 | Evidências funcionais (prints, logs ou testes) | `docs/evidencias.md` contém os roteiros e imagens de cadastro, login, 2FA, sessão, logout e bloqueio; `tests/test_sessions.py` e `tests/test_login_lockout.py` cobrem os fluxos. |
| 1.9 | Sessões com tempo de expiração | `backend/app/utils/sessions.py`, função `create_session`, define expiração de 30 minutos; modelo `Session.expires_at` em `backend/app/models.py`. |
| 1.10 | Invalidação de sessão no logout | `backend/app/utils/sessions.py`, função `revoke_session`, preenche `revoked_at`; `tests/test_sessions.py`, fluxo real de login e logout; `docs/img/5-logout.png`. |
| 1.11 | Proteção contra força bruta (rate limit, bloqueio, atraso) | `backend/app/routes/auth.py` e `backend/app/utils/rate_limit.py` aplicam bloqueio por tentativas e limites por IP; `tests/test_login_lockout.py` e `tests/test_rate_limit.py`. |
| 1.12 | Justificativas técnicas documentadas | `docs/autenticacao.md` justifica sessão no servidor, bloqueio temporário, bcrypt, enumeração e 2FA; `docs/analise-riscos.md` relaciona riscos e contramedidas. |

## 2. Recuperação de Senha

| Nº | Requisito | Evidência no repositório |
|---|---|---|
| 2.1 | Funcionalidade de recuperação de senha implementada | `backend/app/routes/auth.py`, rotas `/auth/forgot-password` e `/auth/reset-password`; `frontend/index.html`, seções de recuperação e redefinição. |
| 2.2 | Token criptograficamente seguro | `backend/app/utils/password_reset.py`, função `generate_reset_token`, usa `secrets.token_urlsafe(32)`; apenas o hash é salvo em `PasswordResetToken.token_hash`. |
| 2.3 | Token com tempo de expiração | `backend/app/routes/auth.py` define `expires_at` para 15 minutos; modelo `PasswordResetToken.expires_at` em `backend/app/models.py`; `docs/recuperacao-senha.md`, seção 3.2. |
| 2.4 | Token invalidado após uso | `backend/app/routes/auth.py` marca `PasswordResetToken.used_at` e revoga sessões; `docs/recuperacao-senha.md`, seção 3.3. |
| 2.5 | Falha correta para token expirado | `backend/app/routes/auth.py` rejeita tokens expirados ou usados; `docs/evidencias-recuperacao-senha.md`, seção “Token expirado”, com `docs/img/16-token-expirado.png`. |
| 2.6 | Registro de solicitação de recuperação em log | `backend/app/utils/password_reset.py`, função `log_password_reset_event`; `PasswordResetLog` registra o evento `request` em `backend/app/models.py`. |
| 2.7 | Registro de sucesso/falha do processo | `backend/app/utils/password_reset.py` registra `success` e `failure`; `docs/auditoria-logs.md`, seção `password_reset_logs`; `docs/img/17-token-reutilizado.png`. |

## 3. Criptografia e Comunicação Segura

| Nº | Requisito | Evidência no repositório |
|---|---|---|
| 3.1 | Comunicação protegida por TLS/HTTPS | `backend/run.py` inicia o Flask com `ssl_context=("cert.pem", "key.pem")` quando os certificados existem; `gerar_certificados.sh` gera os certificados locais; `docs/criptografia.md`. |
| 3.2 | Bloqueio de conexões não seguras | `backend/app/__init__.py` contém o `before_request` que bloqueia HTTP quando `SECURE_COOKIES=true`; `docs/criptografia.md`, seção 1.1. |
| 3.3 | Evidência de tráfego cifrado | `docs/img/24-rota-sem-sessão.png` e `docs/img/22-protecao-logs.png` registram validações em ambiente local; configuração TLS documentada em `docs/criptografia.md` e executável por `backend/run.py`. |
| 3.4 | Dados sensíveis criptografados em repouso | `backend/app/models.py`, tipo `EncryptedTOTPSecret`; `backend/app/two_factor.py`, funções `encrypt_totp_secret` e `decrypt_totp_secret`; `docs/criptografia.md`, seção 2.1. |
| 3.5 | Uso de algoritmo criptográfico adequado (ex.: AES) | `backend/app/two_factor.py` usa `cryptography.fernet.Fernet`, que fornece cifragem autenticada; hashes SHA-256 são usados para tokens em `backend/app/utils/sessions.py` e `password_reset.py`. |
| 3.6 | Chaves criptográficas protegidas | `backend/app/two_factor.py` lê `TOTP_ENCRYPTION_KEY` do ambiente; `backend/app/__init__.py` exige `SECRET_KEY`; `.env.example` documenta ambas sem valores secretos. |
| 3.7 | Estratégia de criptografia documentada | `docs/criptografia.md` descreve proteção em trânsito, TOTP em repouso, Fernet e separação das chaves; `docs/autenticacao.md` descreve hashes de senha e sessão. |
| 3.8 | Justificativa técnica das escolhas | `docs/criptografia.md` justifica TLS, Fernet e isolamento das chaves; `docs/autenticacao.md`, seções sobre bcrypt, sessões e TOTP, registra as decisões de segurança. |

## 4. Conformidade com a LGPD

| Nº | Requisito | Evidência no repositório |
|---|---|---|
| 4.1 | Listagem completa dos dados pessoais coletados | Tabela “Dados pessoais coletados e justificativa” em `docs/dados-pessoais.md`; campos correspondentes em `backend/app/models.py`. |
| 4.2 | Associação de cada dado a uma finalidade | Colunas “Finalidade” e “Por que é necessário” em `docs/dados-pessoais.md`; formulário de cadastro em `frontend/index.html`. |
| 4.3 | Evidência de minimização de dados | Seções “Dados explicitamente não coletados” e “Verificação dos formulários” em `docs/dados-pessoais.md`; `backend/app/routes/lgpd.py` exporta apenas os dados necessários. |
| 4.4 | Registro explícito de consentimento | `frontend/index.html`, checkbox obrigatório `#consent`; `backend/app/routes/auth.py` rejeita cadastro sem consentimento; campos `consent_given_at` e `consent_version` em `User`. |
| 4.5 | Consentimento associado à finalidade | Texto do checkbox em `frontend/index.html` informa conta, autenticação e monitorias; `docs/lgpd.md`, seção “Base Legal e Consentimento”. |
| 4.6 | Possibilidade de revogação do consentimento | `backend/app/routes/auth.py`, rota `/auth/consent/revoke`; `docs/evidencias-lgpd.md`, seção “Revogação, exclusão e tentativa posterior de acesso”. |
| 4.7 | Registro de data e versão do consentimento | `User.consent_given_at` e `User.consent_version` em `backend/app/models.py`; `docs/lgpd.md`, seção 1; exportação em `backend/app/routes/lgpd.py`. |
| 4.8 | Funcionalidade de consulta aos dados do titular | `backend/app/routes/lgpd.py`, função `export_data`, seção “Dados pessoais”; tela “Meus dados” em `frontend/index.html`; `docs/img/27-lgpd-meus-dados.png`. |
| 4.9 | Funcionalidade de exportação dos dados | Rota `/lgpd/export` em `backend/app/routes/lgpd.py` retorna JSON; `docs/img/28-lgpd-exportacao-json.png`; validação em `docs/evidencias-lgpd.md`. |
| 4.10 | Funcionalidade de exclusão dos dados pessoais | Rota `DELETE /lgpd/delete` em `backend/app/routes/lgpd.py`, confirmação de senha e exclusão em cascata; `docs/img/30-lgpd-exclusao-conta.png`. |
| 4.11 | Fluxo de atendimento aos direitos documentado | `docs/lgpd.md` descreve acesso, correção, revogação e eliminação; `docs/dados-pessoais.md` documenta confirmação de identidade e cascata. |

## 5. Auditoria e Logs

| Nº | Requisito | Evidência no repositório |
|---|---|---|
| 5.1 | Logs de autenticação registrados | Modelo `SecurityLog` em `backend/app/models.py`; chamadas a `log_security_event` em `backend/app/routes/auth.py`; `docs/auditoria-logs.md`, seção 1.1. |
| 5.2 | Logs de falhas e 2FA registrados | Eventos `login_failure`, `twofa_failure` e motivos em `SecurityLog`; `docs/auditoria-logs.md`; `tests/test_audit_xss.py` também valida registros de entradas anônimas. |
| 5.3 | Proteção contra alteração dos logs | `backend/db/log_permissions.sql` concede apenas `SELECT, INSERT` e revoga `UPDATE, DELETE`; procedimento e resultado esperado em `docs/logs-imutaveis.md`. |
| 5.4 | Exemplo de análise de logs apresentado | `backend/app/routes/admin.py`, rota `/admin/logs`, agrega métricas e os 20 eventos recentes; `docs/img/23-painel-logs.png`; `docs/auditoria-logs.md`, seção 3. |

## 6. Documentação Técnico-Científica

| Nº | Requisito | Evidência no repositório |
|---|---|---|
| 6.1 | Documento de visão geral do sistema | `docs/visao-geral.md` apresenta objetivo, arquitetura, módulos, stack e fluxo de requisição. |
| 6.2 | Diagrama de arquitetura | Diagrama Mermaid “Visão dos componentes” em `docs/visao-geral.md`. |
| 6.3 | Fluxos de autenticação e dados documentados | Diagramas Mermaid em `docs/autenticacao.md` e `docs/recuperacao-senha.md`; fluxo de dados LGPD em `docs/evidencias-lgpd.md`. |
| 6.4 | Gestão de credenciais documentada | `docs/autenticacao.md`, seção “Gestão de credenciais e criptografia”; `docs/dados-pessoais.md`, campo de senha como hash + salt. |
| 6.5 | Uso de criptografia documentado | `docs/criptografia.md` e `docs/autenticacao.md` detalham bcrypt, SHA-256, Fernet, TOTP e TLS. |
| 6.6 | Identificação dos ativos do sistema | `docs/analise-riscos.md`, seção 2, lista dados, credenciais, TOTP, sessões, tokens, logs, banco, servidor, SMTP e navegador. |
| 6.7 | Identificação de ameaças e vulnerabilidades | `docs/analise-riscos.md`, seção 3, relaciona ameaças e impactos por ativo. |
| 6.8 | Associação risco × contramedida | `docs/analise-riscos.md`, seção 4, matriz de riscos, ativos, nível, contramedida e situação. |
| 6.9 | Testes de segurança realizados | `docs/testes-seguranca.md` documenta testes de força bruta, token, sessão, logs, SQL injection, XSS e hash de sessão; casos automatizados em `tests/`. |
| 6.10 | Resultados dos testes documentados | `docs/testes-seguranca.md` registra execução, resultado “Passou”, evidências visuais e resumo dos sete testes. |
| 6.11 | Uso de artigos científicos e/ou normas técnicas | `docs/referencias.md` cita NIST SP 800-63B, RFC 6238, OWASP Top 10, LGPD e obras de Fontes e Hintzbergen; essas referências são usadas em `docs/autenticacao.md` e `docs/lgpd.md`. |
| 6.12 | Referências normalizadas | `docs/referencias.md` centraliza as referências bibliográficas, normativas e legais em formato ABNT, com autores, títulos, edição, ano e links. |

## 7. Resumo Científico

| Nº | Requisito | Evidência no repositório |
|---|---|---|
| 7.1 | Resumo entre 200 e 300 palavras | `summit/mentory-resumo.pdf`, página 1, seção “Resumo”, apresenta o resumo científico do projeto. |
| 7.2 | Objetivo claramente definido | `summit/mentory-resumo.pdf`, seção “Objetivo”; também aparece no pôster em `summit/Poster-Mentory.pdf`. |
| 7.3 | Metodologia técnica descrita | `summit/mentory-resumo.pdf`, seção “Métodos”, descreve Flask, PostgreSQL, frontend e boas práticas; pôster, seção “METODOLOGIA”. |
| 7.4 | Mecanismos de segurança apresentados | `summit/mentory-resumo.pdf` apresenta bcrypt, salt, TOTP, sessões, bloqueio e recuperação; `summit/Poster-Mentory.pdf` visualiza BCRYPT, 2FA/TOTP, TIME-LOCK e auditoria. |
| 7.5 | Conformidade com a LGPD explicitada | `summit/mentory-resumo.pdf`, seção “Resultados”, explicita consentimento, revogação, consulta, exportação e exclusão; pôster destaca a LGPD. |
| 7.6 | Terminologia técnica adequada | `summit/mentory-resumo.pdf` emprega termos como hash bcrypt, TOTP, SMTP com STARTTLS, sessão, token e LGPD; terminologia é detalhada nos documentos técnicos em `docs/`. |
| 7.7 | Qualidade textual e científica | `summit/mentory-resumo.pdf` apresenta título, resumo, abstract, resumen, palavras-chave, objetivo, métodos, resultados e conclusão em publicação de três páginas. |

## 8. Pôster Científico e Apresentação

| Nº | Requisito | Evidência no repositório |
|---|---|---|
| 8.1 | Estrutura científica do pôster | `summit/Poster-Mentory.pdf` organiza o conteúdo em introdução, objetivo, metodologia, resultados e fluxo de dados; `summit/mentory-poster.png` é a versão visual do pôster. |
| 8.2 | Arquitetura e fluxos representados visualmente | `summit/Poster-Mentory.pdf` contém “Arquitetura monolítica em camadas”, fluxo de dados e fluxo de autenticação; `docs/visao-geral.md` contém o diagrama Mermaid correspondente. |
| 8.3 | Evidência de conformidade com LGPD | `summit/Poster-Mentory.pdf` mostra consentimento com data e versão, portabilidade JSON e consulta, revogação e exclusão; imagens funcionais em `docs/img/26-lgpd-cadastro-consentimento.png` a `30-lgpd-exclusao-conta.png`. |
| 8.4 | Qualidade técnica dos diagramas | `summit/Poster-Mentory.pdf` apresenta os fluxos de dados e autenticação com componentes identificados; os diagramas técnicos editáveis estão em Mermaid em `docs/visao-geral.md` e `docs/autenticacao.md`. |
| 8.5 | Coerência com o sistema entregue | Os mecanismos do pôster, incluindo Flask, PostgreSQL, SQLAlchemy, SMTP, bcrypt, TOTP, sessões, time-lock e auditoria, correspondem aos módulos em `backend/app/`, conforme `docs/visao-geral.md`. |
| 8.6 | Domínio técnico na apresentação | `summit/Poster-Mentory.pdf` sintetiza a arquitetura, metodologia, controles e resultados que são detalhados e rastreáveis em `docs/visao-geral.md`, `docs/autenticacao.md` e `docs/testes-seguranca.md`. |
| 8.7 | Capacidade de resposta às perguntas | `summit/mentory-resumo.pdf`, `summit/Poster-Mentory.pdf` e `docs/referencias.md` fornecem, respectivamente, síntese científica, material visual e fundamentação normativa para sustentar a apresentação técnica. |

## Referência do checklist

O checklist oficial utilizado para este mapeamento está em
[`docs/Requisitos.pdf`](Requisitos.pdf).
