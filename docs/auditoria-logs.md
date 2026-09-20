# Auditoria e Logs

Este documento detalha a estratégia de auditoria de segurança implementada na plataforma Mentory, visando rastreabilidade de acessos e conformidade com boas práticas de segurança defensiva.

## 1. Eventos Auditados
A aplicação mantém o registro histórico e imutável de eventos sensíveis divididos em dois modelos de dados:

### 1.1 Logs de Autenticação e 2FA (`security_logs`)
Registra tentativas de acesso e validação de fatores de autenticação:
* `login_success`: Autenticação primária bem-sucedida.
* `login_failure`: Falha na autenticação primária (senha incorreta, usuário inexistente, conta bloqueada).
* `twofa_success`: Validação bem-sucedida do código TOTP.
* `twofa_failure`: Código TOTP incorreto ou expirado.

Para garantir privacidade e segurança:
* Senhas e segredos (secrets do TOTP) **nunca** são registrados em texto claro.
* O e-mail utilizado na tentativa é registrado para permitir a investigação mesmo se a conta do usuário for posteriormente excluída.

### 1.2 Logs de Recuperação de Senha (`password_reset_logs`)
Registra o ciclo de vida dos tokens de recuperação:
* `request`: Solicitação de link de recuperação enviada.
* `success`: Senha redefinida com sucesso.
* `failure`: Tentativa de uso de token expirado ou inválido.

## 2. Proteção contra Violação de Logs (Anti-Tampering)
Para garantir a integridade da trilha de auditoria e impedir que invasores apaguem seus rastros, a proteção foi implementada na **camada de banco de dados**.

As permissões do usuário do banco utilizado pela aplicação (`DB_APP_USER`) foram restritas especificamente para as tabelas `security_logs` e `password_reset_logs`:
* `GRANT INSERT, SELECT`: A aplicação pode inserir novos logs e consultar o histórico para análise.
* `REVOKE UPDATE, DELETE`: A aplicação tem **permissão negada** pelo PostgreSQL caso tente alterar ou apagar qualquer log existente. Nenhuma rota ou injeção de SQL será capaz de burlar esta restrição no nível da aplicação.

## 3. Painel de Análise
Uma interface de análise foi disponibilizada para consolidar as métricas de segurança, visível apenas para contas configuradas na variável de ambiente `ADMIN_EMAIL`.

O painel exibe:
1. Agregadores de incidentes críticos: Totais de sucessos e falhas de login, falhas de 2FA e requisições de senha.
2. Trilha em tempo real: Lista unificada dos 20 eventos mais recentes do sistema (Data, E-mail envolvido, Tipo de Evento e Detalhes da Falha).

*(Insira aqui o Print da tela do Painel de Auditoria funcionando com dados reais)*
