# Auditoria e Logs

Este documento detalha a estratégia de auditoria de segurança implementada na plataforma Mentory, visando rastreabilidade de acessos e conformidade com boas práticas de segurança defensiva.

## 1. Eventos Auditados
Alinhada às diretrizes da **OWASP Top 10** sobre *Security Logging and Monitoring Failures*, a aplicação mantém o registro histórico e imutável de eventos sensíveis divididos em dois modelos de dados:

### 1.1 Logs de Autenticação e 2FA (`security_logs`)
Registra tentativas de acesso e validação de fatores de autenticação:
* `login_success`: Autenticação primária bem-sucedida.
* `login_failure`: Falha na autenticação primária (senha incorreta, usuário inexistente, conta bloqueada).
* `twofa_success`: Validação bem-sucedida do código TOTP.
* `twofa_failure`: Código TOTP incorreto ou expirado.

Para garantir privacidade e segurança:
* Senhas e segredos (secrets do TOTP) **nunca** são registrados em texto claro.
* O e-mail utilizado na tentativa é registrado para permitir a investigação mesmo se a conta do usuário for posteriormente excluída.
* O e-mail em cada evento é dado pessoal temporário: após **90 dias**, ele é
  substituído por um pseudônimo estável (`redacted+<hash>@example.invalid`).
  O evento, seu tipo, motivo e data são preservados para análise de segurança.

### 1.2 Logs de Recuperação de Senha (`password_reset_logs`)
Registra o ciclo de vida dos tokens de recuperação:
* `request`: Solicitação de link de recuperação enviada.
* `success`: Senha redefinida com sucesso.
* `failure`: Tentativa de uso de token expirado ou inválido.

## 2. Proteção contra Violação de Logs (Anti-Tampering)
Conforme discutido por Hintzbergen et al. (2018), o princípio da "Integridade" no Triângulo CIA (Confidencialidade, Integridade e Disponibilidade) assegura que a informação permaneça completa, perfeita e inalterada de forma não autorizada. Para garantir a integridade absoluta da trilha de auditoria e impedir que invasores apaguem seus rastros, a proteção foi implementada na **camada de banco de dados**.

As permissões do usuário do banco utilizado pela aplicação (`DB_APP_USER`) foram restritas especificamente para as tabelas `security_logs` e `password_reset_logs`:
* `GRANT INSERT, SELECT`: A aplicação pode inserir novos logs e consultar o histórico para análise.
* `REVOKE UPDATE, DELETE`: A aplicação tem **permissão negada** pelo PostgreSQL caso tente alterar ou apagar qualquer log existente. Nenhuma rota ou injeção de SQL será capaz de burlar esta restrição no nível da aplicação.

### 2.1 Retenção e exceções de investigação

A finalidade dos logs é detectar força bruta, investigar incidentes e comprovar
eventos de autenticação e recuperação de senha. A retenção do e-mail em claro é
limitada a 90 dias, prazo suficiente para a investigação operacional ordinária.
Depois desse prazo, a rotina administrativa
`backend/db/anonymize_old_log_emails.sql` pseudonimiza o e-mail sem apagar ou
alterar os demais campos do evento.

Uma investigação ativa pode criar uma exceção em
`log_retention_exemptions`, sempre com referência ao par `(log_table, log_id)`,
justificativa e data de expiração. Essa tabela administrativa é provisionada
por `backend/db/log_retention_setup.sql`, com a credencial do banco, e não
recebe permissões da role da aplicação. Exceções são temporárias e devem ser
removidas ou expiradas ao encerrar o incidente; não existe retenção indefinida
por padrão. O uso detalhado e o comando de inclusão estão documentados em
`docs/logs-imutaveis.md`.

## 3. Painel de Análise
Uma interface de análise foi disponibilizada para consolidar as métricas de segurança, visível apenas para contas com acesso administrativo, concedido exclusivamente pelo comando `provision-admin` (veja a seção 4).

O painel exibe:
1. Agregadores de incidentes críticos: Totais de sucessos e falhas de login, falhas de 2FA e requisições de senha.
2. Trilha em tempo real: Lista unificada dos 20 eventos mais recentes do sistema (Data, E-mail envolvido, Tipo de Evento e Detalhes da Falha). Eventos antigos exibem o pseudônimo, conforme a política de retenção.

*(Insira aqui o Print da tela do Painel de Auditoria funcionando com dados reais)*


## 4. Provisionamento do administrador

O acesso ao painel depende da coluna `users.is_admin`, que o cadastro nunca altera. Sem nenhuma conta provisionada, o painel fica inacessível (`403`).

Para conceder o acesso, a conta precisa existir. Execute, a partir da pasta `backend` e com o ambiente virtual ativo:

```bash
flask --app app provision-admin EMAIL_DA_CONTA
```

O comando mostra o id, o usuário e o nome da conta e pede confirmação. Confira que a conta é realmente a do administrador antes de confirmar. Para remover o acesso, use `--revoke`. A revogação vale na próxima requisição, porque `is_admin` é lido do banco a cada acesso.

Bancos já existentes precisam da coluna nova:

```bash
ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE;
```

Depois da migração, ninguém é administrador até rodar o comando.

## Referências
Para consultar as referências bibliográficas, científicas e normativas que fundamentam as decisões deste documento, consulte as **[Referências Técnicas](referencias.md)**.
