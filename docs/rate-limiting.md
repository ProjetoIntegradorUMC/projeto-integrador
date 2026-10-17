# Rate Limiting

Esse documento descreve a limitação de requisições aplicada aos fluxos públicos de cadastro e recuperação de senha.

## 1. Política

| Operação | Escopo | Limite | Janela |
| --- | --- | --- | --- |
| `register` (`/auth/register`) | IP | 10 requisições | 1 hora |
| `forgot_password` (`/auth/forgot-password`) | IP | 5 requisições | 15 minutos |
| `forgot_password` (`/auth/forgot-password`) | e-mail | 3 requisições | 1 hora |

Os valores ficam em `LIMITS`, em `backend/app/utils/rate_limit.py`.

### Por que esses valores

- **Cadastro, 10 por hora por IP:** o usuário legítimo se cadastra uma vez. O limite é maior que 1 porque alunos de uma mesma rede compartilham o mesmo IP. Cada tentativa custa um hash bcrypt, que é o recurso que o abuso consome.
- **Recuperação, 5 por 15 minutos por IP:** cobre os erros de digitação e novas tentativas, e barra automações. A janela possui a validade de 15 minutos do token.
- **Recuperação, 3 por hora por e-mail:** o usuário raramente precisa de mais de 3 links por hora. Esse limite protege a caixa de entrada e a cota SMTP, mesmo contra ataques vindos de vários IPs.

## 2. Resposta ao limite

- **Por IP:** `429 Too Many Requests`, com o cabeçalho `Retry-After` (segundos) e a mensagem "Muitas tentativas. Tente novamente em X minutos." A decisão não depende do e-mail enviado.
- **Por e-mail:** o mesmo `200` genérico de um pedido normal, sem enviar e-mail. O contador conta e-mails existentes e inexistentes, então a resposta não revela se a conta existe ou não.
- **Resposta genérica na recuperação:** e-mails existentes, inexistentes e falhas de envio SMTP retornam o mesmo `200`. A falha de envio continua registrada em `password_reset_logs`.

## 3. Armazenamento

Os contadores ficam na tabela `rate_limit_counters` do PostgreSQL, então os limites não reiniciam a cada processo.

- Janela fixa, com um `INSERT ... ON CONFLICT DO UPDATE`, que é atômico entre processos.
- Contadores expirados são apagados de forma oportunista, sem tarefa agendada.
- A tabela é criada pelo `db.create_all()`; não é necessária migração manual.

A lógica fica isolada em `rate_limit.py`. Se o tráfego crescer, o armazenamento pode migrar para Redis sem alterar as rotas.

## 4. Privacidade e logs

- A chave do contador usa um HMAC (com a `SECRET_KEY`) do IP ou do e-mail, nunca o valor puro.
- O primeiro bloqueio de cada janela gera um evento `rate_limited` em `security_logs`, com `failure_reason` `register_ip`, `forgot_password_ip` ou `forgot_password_email`. O IP não é gravado. Senhas e tokens nunca entram no log.
- Só o primeiro bloqueio da janela é registrado, para um atacante não encher a trilha da auditoria.

## 5. Limitações conhecidas

- **Proxy reverso:** o IP vem de `request.remote_addr`. Atrás de um proxy, ele seria o IP do proxy, e todos os usuários dividiriam o mesmo limite. No deploy, configure o `ProxyFix` do werkzeug com o número exato de proxies confiáveis e altere apenas `get_client_ip()`. Confiar em `X-Forwarded-For` sem esse cuidado permite forjar o IP.
- **Limite por e-mail:** um atacante pode esgotar os 3 pedidos de uma vítima e impedir novos links por até 1 hora. Links já enviados continuam válidos por 15 minutos.
- **Tempo de resposta:** o envio de e-mail é síncrono, então a resposta para contas existentes é mais lenta. O envio em segundo plano eliminaria essa diferença.