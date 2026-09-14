# Conformidade com a LGPD (Lei Geral de Proteção de Dados)

Este documento detalha as diretrizes técnicas e as funcionalidades implementadas no sistema Mentory para garantir a adequação à Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018).

## 1. Base Legal e Consentimento
O tratamento dos dados pessoais no sistema é pautado na base legal do **Consentimento** (Art. 7º, I, da LGPD).

- **Coleta:** O consentimento é exigido e registrado de forma obrigatória no momento do cadastro do usuário.
- **Registro:** O sistema armazena a data e a hora exata da concessão (`consent_given_at`) bem como a versão do termo aceito (`consent_version`).
- **Transparência:** O texto de consentimento informa explicitamente as finalidades do uso dos dados (criação da conta, gerenciamento de monitorias e contato).

## 2. Direitos do Titular (Art. 18 da LGPD)
O sistema disponibiliza, através do painel do usuário, recursos para consulta dos dados da conta e revogação do consentimento. Quando o direito solicitado ainda não possui uma operação automatizada, o titular recebe uma orientação de atendimento.

### 2.1 Direito de Acesso e Portabilidade
O usuário pode visualizar no painel os dados básicos associados à sua conta, como nome completo, nome de usuário e e-mail.

O download estruturado de todos os dados pessoais ainda não está disponível na versão atual da aplicação. Dados técnicos de segurança, como o *hash* da senha e a chave secreta do Autenticador de Duas Etapas (2FA), não são exibidos ao usuário.

### 2.2 Direito de Correção dos Dados
Para solicitar a alteração ou correção de seus dados cadastrais, o titular deve entrar em contato pelo e-mail **projetomentory@gmail.com**. Essa orientação é o mecanismo provisório adotado enquanto não existe uma tela de edição de dados no sistema.

### 2.3 Direito à Eliminação dos Dados e Revogação
Conforme a LGPD, a revogação do consentimento para a manutenção da conta inviabiliza a base legal para o armazenamento dos dados.
- **Exclusão Definitiva:** O titular possui um botão de "Excluir minha conta definitivamente".
- **Revogação:** O titular também pode revogar o consentimento no painel. A revogação implica a exclusão definitiva da conta.
- **Cascata (On Delete Cascade):** O banco de dados está modelado de forma relacional estrita. Ao excluir a conta, o sistema apaga automaticamente e em cascata todas as sessões ativas (`sessions`), ofertas de monitoria (`tutoring_offers`) e inscrições realizadas (`enrollments`). Isso garante a eliminação completa e mitiga o risco de dados órfãos.

## 3. Segurança dos Dados
Para garantir a integridade e segurança (Art. 6º, VIII) dos dados pessoais armazenados, o Mentory implementa:
- **Criptografia:** Senhas protegidas via *Hashing* (Bcrypt) com *Salt* gerado aleatoriamente.
- **MFA (Multi-Factor Authentication):** Suporte opcional à autenticação em duas etapas usando algoritmo TOTP (Time-based One-time Password).
- **Gerenciamento de Sessão:** Controle estrito do ciclo de vida da sessão do usuário, incluindo expiração e anulação de sessão após a exclusão da conta.
