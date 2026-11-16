# Mapeamento e minimização de dados pessoais do Mentory

## Objetivo

Este documento registra os dados pessoais coletados pelo Mentory, a finalidade de cada coleta e a justificativa de necessidade, conforme a regra de minimização de dados da LGPD.

## Dados pessoais coletados e justificativa

| Dado pessoal | Onde é coletado | Finalidade | Por que é necessário | Proteção em repouso |
|---|---|---|---|---|
| Nome completo (`User.full_name`) | Cadastro | Identificar o usuário na plataforma (quem é o monitor, quem é o mentorado) | Um sistema de conexão entre pessoas não funciona de forma anônima | `controle de acesso PostgreSQL` — dado cadastral de exibição pública na plataforma (não é dado sensível nos termos do art. 5º, II, da LGPD); protegido pelo isolamento de rede do banco e privilégios mínimos da role de runtime (`app_role_setup.sql`). |
| Nome de usuário (`User.username`) | Cadastro | Identificar a conta de forma única e exibir um identificador na plataforma | É usado para diferenciar contas e compor a identificação do usuário no sistema | `controle de acesso PostgreSQL` — identificador único usado em consultas indexadas (`UNIQUE`); cifragem não determinística (Fernet) inviabilizaria buscas diretas sem ganho contra comprometimento do runtime. |
| E-mail (`User.email`) | Cadastro | Login e canal de recuperação de senha | Único dado de contato coletado; usado só para autenticação e recuperação | `controle de acesso PostgreSQL` — exigido em texto claro para localização da conta no login (`SELECT` em `users`) e disparo de recuperação de senha; protegido por privilégios mínimos no PostgreSQL e isolamento de rede. |
| Senha (`User.password_hash`) | Cadastro | Autenticar o usuário no login | Nunca fica em texto puro; só o hash irreversível é salvo | `bcrypt` — hash unidirecional com salt aleatório por registro; cifra simétrica seria redundante e impediria a verificação segura sem reversão. |
| Segredo do 2FA (`User.two_factor_secret`) | Ativação do 2FA no perfil | Gerar/validar o segundo fator no login | Só existe para quem ativa o 2FA por opção própria | `Fernet (EncryptedTOTPSecret)` — credencial criptográfica de alta sensibilidade que precisa ser decifrada em memória para cálculo e validação dos códigos TOTP temporários. |
| Token de recuperação de senha (`PasswordResetToken.token_hash`) | Solicitação de "Esqueci minha senha" | Permitir redefinir a senha com segurança | Temporário, expira em minutos e é invalidado após o uso | `controle de acesso PostgreSQL` — armazenado exclusivamente como digest hash SHA-256 (`token_hash`), nunca em texto puro, aliado às restrições da role do banco. |
| Registros de tentativas de login e de recuperação (`SecurityLog.email`, `PasswordResetLog.email`) | Login e recuperação de senha | Detectar força bruta e auditar o processo | Exigência de segurança já prevista nas entregas do projeto; e-mail em claro por 90 dias, depois pseudonimizado | `pseudonimização (90 dias)` — retido em claro apenas pelo prazo operacional de investigação e substituído por pseudônimo estável via `backend/db/anonymize_old_log_emails.sql`; role da app não possui `UPDATE`/`DELETE` nos logs. |
| Data/hora e versão do consentimento (`User.consent_given_at`, `User.consent_version`) | Cadastro (aceite dos termos) | Comprovar que o titular consentiu, e com qual versão dos termos | Exigência direta desta entrega | `controle de acesso PostgreSQL` — metadado de auditoria jurídica sem conteúdo sensível; protegido pelas permissões restritas da tabela `users`. |
| Disciplina oferecida ou buscada (`TutoringOffer.subject`, `description`) | Oferta de monitoria / inscrição | Conectar quem oferece ajuda numa disciplina com quem precisa dela | É a funcionalidade central do Mentory; sem esse dado o sistema de monitoria não existe | `controle de acesso PostgreSQL` — dado operacional público dentro da plataforma, protegido pelos controles de acesso da tabela `tutoring_offers`. |
| Registro do relacionamento (`Enrollment.user_id`, `tutoring_offer_id`) | Inscrição em uma monitoria | Formalizar a conexão entre monitor e mentorado para que ambos acompanhem a monitoria | Necessário para o funcionamento básico da monitoria; ambas as partes precisam saber que estão conectadas | `controle de acesso PostgreSQL` — chave relacional entre usuário e oferta na tabela `enrollments`, protegida por privilégios mínimos da role da aplicação. |

### Justificativa técnica da proteção em repouso por campo (`models.py`)

A escolha do mecanismo de proteção em repouso segue o modelo de ameaças da aplicação e a natureza operacional de cada atributo:

1. **`User.password_hash` (`bcrypt`):** Senhas são verificadas por comparação de hash, nunca recuperadas em texto claro. O uso de `bcrypt` com salt individual garante resistência a ataques de força bruta e tabelas rainbow, tornando qualquer cifra simétrica adicional desnecessária.
2. **`User.two_factor_secret` (`Fernet` via `EncryptedTOTPSecret`):** Diferente da senha, o algoritmo TOTP exige o segredo compartilhado original em Base32 para gerar e validar os códigos de 6 dígitos a cada janela de 30 segundos. Por exigir reversibilidade em memória e representar uma credencial crítica de autenticação, o campo recebe cifragem simétrica autenticada (Fernet) com chave isolada em `TOTP_ENCRYPTION_KEY`.
3. **`User.email`, `User.full_name` e `User.username` (`controle de acesso PostgreSQL`):** Não configuram dados pessoais sensíveis (art. 5º, II, da LGPD) e são indispensáveis para consultas relacionais (`SELECT` por `email` ou `username` no login e exibição de `full_name` nas ofertas de monitoria). Como o Fernet gera tokens não determinísticos (IV aleatório a cada cifragem), aplicá-lo a esses campos impediria índices `UNIQUE` e buscas exatas no banco. Além disso, em um cenário de comprometimento da aplicação em execução, o atacante já teria acesso à `TOTP_ENCRYPTION_KEY` em memória. A proteção adequada concentra-se, portanto, no isolamento de rede do PostgreSQL e no princípio do menor privilégio definido em `backend/db/app_role_setup.sql` (`DB_APP_USER` associado à role `DB_APP_ROLE` sem superuser, sem DDL e com grants explícitos apenas nas tabelas necessárias).
4. **`SecurityLog.email` e `PasswordResetLog.email` (`pseudonimização` após 90 dias):** Para investigar incidentes de força bruta e abuso na recuperação de senha, o e-mail precisa estar legível no curto prazo. Após 90 dias, a rotina administrativa `backend/db/anonymize_old_log_emails.sql` substitui o endereço por `redacted+<md5>@example.invalid`, preservando a correlação estatística sem manter o dado pessoal em claro indefinidamente.

## Dados explicitamente não coletados

A coleta do Mentory é limitada ao necessário. Os dados abaixo não constam do fluxo atual e, por isso, não são armazenados nem solicitados:

- CPF
- Telefone
- Endereço
- Data de nascimento
- Gênero
- Foto
- Papel de coordenação
- Matching automático, avaliação, reputação e agendamento

### Por que a coordenação fica de fora

O sistema atual não implementa uma funcionalidade de coordenação, nem qualquer requisito operacional que dependa de atribuir papel institucional ao usuário. Incluir esse dado sem uso concreto geraria coleta desnecessária e violaria o princípio de minimização previsto na LGPD.

## Verificação dos formulários

Conforme a análise do frontend atual, os fluxos principais do Mentory coletam apenas os dados necessários para a funcionalidade do sistema:

- Cadastro: nome completo, nome de usuário, e-mail, senha e aceite obrigatório dos termos. O aceite gera a data/hora e a versão do consentimento no backend.
- Oferta de monitoria: disciplina e descrição da oferta.
- Inscrição em monitoria: o relacionamento é registrado no contexto da inscrição, sem coleta de dado extra sobre a pessoa além do vínculo monitor/mentorado.

O campo de descrição da oferta é conteúdo operacional da monitoria, não um dado pessoal obrigatório do usuário. A caixa de aceite também não coleta um dado pessoal diretamente; ela registra os metadados de consentimento listados na tabela. A coleta de dados complementares (como foto, telefone, endereço, coordenação, avaliação e reputação) não faz parte do escopo atual e, portanto, não é necessária para a operação do Mentory nesta entrega.

## Eliminação de dados e confirmação de identidade (LGPD Art. 18, VI)

Para garantir que o direito à eliminação definitiva de dados e encerramento de conta seja exercido exclusivamente pelo próprio titular, o Mentory exige **confirmação prévia da senha atual** tanto na rota de exclusão de conta (`DELETE /lgpd/delete`) quanto na revogação de consentimento (`POST /auth/consent/revoke`).

Essa medida atende aos padrões de segurança recomendados (OWASP ASVS V3.2) e mitiga os seguintes riscos:
- **Exclusões acidentais** provocadas por cliques involuntários;
- **Ataques de Cross-Site Request Forgery (CSRF)** ou requisições forçadas a partir de navegadores com sessões abertas;
- **Sessões deixadas abertas em dispositivos compartilhados**, impedindo que terceiros com acesso transitório à interface apaguem a conta sem conhecer a credencial principal.

Todas as exclusões acionam a regra `ON DELETE CASCADE` configurada nos modelos relacionais, garantindo que sessões ativas, ofertas de monitoria e inscrições vinculadas ao titular sejam completamente expurgadas de forma atômica e irreversível - ressalvados os registros históricos de auditoria e eventuais cópias de backup, conforme detalhado na seção **Ciclo de vida pós-exclusão de conta**.

## Conclusão

A coleta atual do Mentory está aderente ao princípio da minimização, pois cada dado solicitado tem finalidade clara, está associado a um fluxo relevante do sistema e não inclui campos que não são necessários para o funcionamento da plataforma.

## Retenção e minimização de e-mails em logs

Os logs `security_logs` e `password_reset_logs` mantêm o e-mail em claro por
90 dias para investigação de incidentes de autenticação e recuperação de senha.
Após esse prazo, a rotina administrativa
`backend/db/anonymize_old_log_emails.sql` substitui o e-mail por um pseudônimo
estável e preserva apenas os metadados necessários (tipo, motivo, data e
eventual vínculo técnico). O registro do evento não é apagado.

Investigações ativas podem receber uma exceção temporária em
`log_retention_exemptions`, identificando a tabela e o `id` do evento, com
justificativa e expiração. Essa tabela de controle não é uma cópia dos logs:
ela guarda somente a referência ao evento e os metadados da exceção. A inclusão
é feita por administrador do banco, conforme o procedimento documentado em
`docs/logs-imutaveis.md`, e não altera a política padrão de 90 dias.

## Ciclo de vida pós-exclusão de conta

Quando o titular aciona `DELETE /lgpd/delete` (ou revoga o consentimento via `POST /auth/consent/revoke`), o destino dos dados pessoais segue prazos distintos conforme a camada de armazenamento:

### 1. Banco de dados ativo (`mentory_pgdata`)
- **Remoção imediata:** A exclusão do registro em `users` aciona `ON DELETE CASCADE` e apaga imediatamente os dados cadastrais, credenciais (`password_hash`, `two_factor_secret`), sessões (`sessions`), tokens de recuperação (`password_reset_tokens`), ofertas de monitoria (`tutoring_offers`) e inscrições (`enrollments`) do volume `mentory_pgdata` do PostgreSQL.

### 2. Logs de auditoria (`security_logs` e `password_reset_logs`)
- **Sem novo registro na exclusão:** A rota `DELETE /lgpd/delete` (`backend/app/routes/lgpd.py`) não grava evento contendo e-mail ou dados pessoais do titular nas tabelas de log no momento da exclusão.
- **Logs históricos anteriores:** Registros prévios de autenticação e recuperação de senha permanecem armazenados por legítimo interesse de segurança (Art. 7º, IX, da LGPD). Com a exclusão da conta, o campo `user_id` passa automaticamente para `NULL` (`ondelete="SET NULL"`), e o campo `email` permanece em claro por **até 90 dias** a contar da data do evento.
- **Pseudonimização após 90 dias:** Decorrido o prazo de 90 dias, a rotina administrativa `backend/db/anonymize_old_log_emails.sql` substitui o e-mail pelo pseudônimo `redacted+<md5>@example.invalid` (salvo exceção formal ativa em `log_retention_exemptions`).

### 3. Backups do volume PostgreSQL
- **Estado atual (limitação conhecida):** Não há rotina automatizada de backup (`pg_dump` agendado ou snapshot automático) configurada no repositório ou no `docker-compose.prod.yml` para o volume `mentory_pgdata` na VPS Hostinger. Assim, na configuração atual, não existem cópias secundárias retendo dados de contas excluídas após a remoção no banco ativo.
- **Diretriz para implantação de backups futuros:** Caso rotinas de backup lógico (`pg_dump`) ou snapshot de volume sejam habilitadas em versões futuras, os arquivos devem ser cifrados em repouso com retenção máxima definida (recomendado até **30 dias** em rotação cíclica), garantindo que dados de contas excluídas sejam eliminados definitivamente na expiração natural do ciclo de retenção, sem restauração seletiva de titulares já excluídos.
