# Conformidade com a LGPD (Lei Geral de Proteção de Dados)

Este documento detalha as diretrizes técnicas e as funcionalidades implementadas no sistema Mentory para garantir a adequação à Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018).

## 1. Base Legal e Consentimento
O tratamento dos dados pessoais no sistema é pautado na base legal do **Consentimento** (Art. 7º, I, da LGPD - BRASIL, 2018). Conforme Fontes (2015) aponta, para o sucesso e o cumprimento da Política de Segurança da Informação, o usuário deve conhecer e estar de acordo com os termos de consentimento, explicitando assim a sua responsabilidade e o alcance do uso de suas informações.

- **Coleta:** O consentimento é exigido e registrado de forma obrigatória no momento do cadastro do usuário.
- **Registro:** O sistema armazena a data e a hora exata da concessão (`consent_given_at`) bem como a versão do termo aceito (`consent_version`).
- **Transparência:** O texto de consentimento informa explicitamente as finalidades do uso dos dados (criação da conta, gerenciamento de monitorias e contato).

## 2. Direitos do Titular (Art. 18 da LGPD - BRASIL, 2018)
O sistema disponibiliza, através do painel do usuário, recursos para consulta dos dados da conta e revogação do consentimento, zelando pelo princípio do livre acesso e transparência exigidos pela legislação. Quando o direito solicitado ainda não possui uma operação automatizada, o titular recebe uma orientação de atendimento.

### 2.1 Direito de Acesso e Portabilidade
O usuário pode visualizar no painel os dados básicos associados à sua conta, como nome completo, nome de usuário e e-mail.

O sistema fornece um botão "Baixar meus dados (JSON)" no painel do usuário, acionando a rota `/lgpd/export`. Essa funcionalidade permite o download estruturado de todos os dados pessoais associados à conta em um arquivo `meus_dados_lgpd.json`. Para a segurança do sistema, dados sensíveis internos como o *hash* da senha e a chave secreta do Autenticador de Duas Etapas (2FA) não são exportados.

### 2.2 Direito de Correção dos Dados
Para solicitar a alteração ou correção de seus dados cadastrais, o titular deve entrar em contato pelo e-mail **projetomentory@gmail.com**. Essa orientação é o mecanismo provisório adotado enquanto não existe uma tela de edição de dados no sistema.

### 2.3 Direito à Eliminação dos Dados e Revogação
Conforme a LGPD(Art. 8º, § 5º e Art. 18, VI e IX), o titular pode solicitar a exclusão da conta ou revogar o consentimento concedido no cadastro, encerrando o tratamento baseado nessa hipótese legal:
- **Exclusão Definitiva:** O titular possui um botão de "Excluir minha conta definitivamente"(`DELETE /lgpd/delete`).
- **Revogação:** O titular também pode revogar o consentimento no painel. A revogação implica a exclusão definitiva da conta. **ressalvada a retenção temporária dos logs de auditoria por legítimo interesse de segurança** (detalhada na seção 2.4).
- **Cascata (On Delete Cascade):** O banco de dados está modelado de forma relacional estrita. Ao excluir a conta, o sistema apaga automaticamente e em cascata todas as sessões ativas (`sessions`), ofertas de monitoria (`tutoring_offers`) e inscrições realizadas (`enrollments`). Isso garante a eliminação completa e mitiga o risco de dados órfãos

### 2.4 Efeito da Revogação do Consentimento
Quando o titular aciona `POST /auth/consent/revoke` (mediante confirmação de senha), o backend executa `db.session.delete(current_user)`, produzindo três efeitos distintos no banco de dados conforme a natureza e a base legal de cada dado:

1. **Excluído diretamente (`users`):**
   - O registro principal do titular na tabela `users` é removido permanentemente, eliminando nome completo (`full_name`), nome de usuário (`username`), endereço de e-mail (`email`), hash da senha (`password_hash`), segredo do segundo fator (`two_factor_secret`), metadados de consentimento (`consent_given_at`, `consent_version`) e contadores de bloqueio de login/2FA.
2. **Excluídos imediatamente via `ON DELETE CASCADE`:**
   - **Sessões (`sessions`):** Todas as sessões ativas ou expiradas vinculadas ao `user_id` são apagadas, além da invalidação imediata do cookie `session_id` na resposta HTTP.
   - **Tokens de recuperação (`password_reset_tokens`):** Eventuais tokens pendentes ou já utilizados vinculados à conta são removidos.
   - **Ofertas de monitoria (`tutoring_offers`):** Todas as ofertas criadas pelo usuário como mentor são excluídas (assim como inscrições de terceiros associadas a essas ofertas).
   - **Inscrições (`enrollments`):** Todas as inscrições do usuário em monitorias são apagadas.
3. **Preservados por base legal distinta do consentimento (`security_logs` e `password_reset_logs`):**
   - As entradas históricas nas tabelas de auditoria `security_logs` e `password_reset_logs` **não são apagadas** na revogação do consentimento.
   - Por configuração relacional (`ondelete="SET NULL"`), a chave estrangeira `user_id` é desvinculada (passando a `NULL`), enquanto o campo `email` permanece legível por até **90 dias** para investigação de incidentes de segurança, tentativas de força bruta ou abuso na recuperação de senha.
   - Após 90 dias, a rotina administrativa `backend/db/anonymize_old_log_emails.sql` substitui o endereço por um pseudônimo estável (`redacted+<md5>@example.invalid`).
   - **Fundamento jurídico:** O tratamento continuado desses registros após a revogação não depende de consentimento, mas sim do **legítimo interesse do controlador para garantia da segurança da informação e prevenção à fraude** (Art. 7º, IX, combinado com o Art. 16, I/IV, da LGPD).

### 2.5 Bases legais por finalidade de tratamento

| Categoria / Dado pessoal | Tabela / Campo (`models.py`) | Finalidade do tratamento | Base legal (Art. 7º, LGPD) | Comportamento após `POST /auth/consent/revoke` |
|---|---|---|---|---|
| Dados cadastrais de identificação (`full_name`, `username`, `email`) | `users` | Criação de conta, identificação entre mentor e mentorado, login e comunicações de recuperação | **Consentimento** (Art. 7º, I) | **Excluído diretamente** com a remoção do registro `User`. |
| Credenciais de autenticação (`password_hash`, `two_factor_secret`) | `users` | Autenticação do titular e proteção de acesso via MFA (TOTP) | **Consentimento** (Art. 7º, I) e **Legítimo interesse / Segurança** (Art. 7º, IX) | **Excluído diretamente** com a remoção do registro `User`. |
| Registro de aceite (`consent_given_at`, `consent_version`) | `users` | Comprovação da manifestação de vontade e versão vigente dos termos | **Cumprimento de obrigação legal/regulatória** (Art. 7º, II; Art. 8º, § 2º) | **Excluído diretamente** com o encerramento da conta. |
| Ofertas e inscrições de monitoria (`subject`, `description`, vínculos) | `tutoring_offers`, `enrollments` | Operacionalização das monitorias acadêmicas entre usuários | **Consentimento** (Art. 7º, I) / **Execução de procedimento preliminar ou serviço solicitado** (Art. 7º, V) | **Excluído imediatamente** via `ON DELETE CASCADE`. |
| Sessões e tokens temporários de senha (`token_hash`) | `sessions`, `password_reset_tokens` | Manutenção da sessão autenticada e fluxo seguro de redefinição de senha | **Legítimo interesse / Segurança da operação** (Art. 7º, IX) | **Excluído imediatamente** via `ON DELETE CASCADE`. |
| Logs de auditoria de login e recuperação (`email`, `event_type`, `created_at`) | `security_logs`, `password_reset_logs` | Rastreabilidade de incidentes, detecção de força bruta e auditoria de segurança | **Legítimo interesse — Segurança e prevenção à fraude** (Art. 7º, IX; Art. 15 e 16) | **Preservado** (`user_id` vira `NULL`); `email` mantido por até 90 dias e depois **pseudonimizado** (`anonymize_old_log_emails.sql`). |
| Contadores de limitação de taxa (digest HMAC de IP/e-mail) | `rate_limit_counters` | Mitigação de abuso, brute force e negação de serviço | **Legítimo interesse — Segurança e prevenção à fraude** (Art. 7º, IX) | **Expiração automática** ao fim da janela curta de rate limit (sem armazenamento de dado em claro). |

## 3. Segurança dos Dados
Para garantir a integridade e segurança (Art. 6º, VIII) dos dados pessoais armazenados, o Mentory implementa:
- **Criptografia:** Senhas protegidas via *Hashing* (Bcrypt) com *Salt* gerado aleatoriamente.
- **MFA (Multi-Factor Authentication):** Suporte opcional à autenticação em duas etapas usando algoritmo TOTP (Time-based One-time Password).
- **Gerenciamento de Sessão:** Controle estrito do ciclo de vida da sessão do usuário, incluindo expiração e anulação de sessão após a exclusão da conta.

## Referências
Para consultar as referências bibliográficas, científicas e normativas que fundamentam as decisões deste documento, consulte as **[Referências Técnicas](referencias.md)**.
