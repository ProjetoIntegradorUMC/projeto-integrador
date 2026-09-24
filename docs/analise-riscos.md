# Análise de riscos e ameaças

Este documento identifica os principais ativos de informação do Mentory, as
ameaças que podem afetá-los e as contramedidas adotadas ou planejadas. A
análise foi feita com base no comportamento atual do código.

## 1. Escopo e critérios

O escopo inclui o backend Flask, o banco de dados PostgreSQL, o navegador do
usuário, o serviço SMTP utilizado na recuperação de senha e os dados tratados
pelos fluxos de autenticação, monitoria e LGPD.

Neste documento, os riscos são classificados de forma qualitativa:

- **Alto:** pode comprometer credenciais, permitir acesso indevido ou causar
  exposição relevante de dados pessoais.
- **Médio:** pode afetar a disponibilidade, a rastreabilidade ou uma parte
  limitada da confidencialidade/integridade.
- **Baixo:** impacto limitado, desde que os controles principais permaneçam
  funcionando.

Uma contramedida marcada como **Pendente** é uma lacuna identificada na
auditoria. Ela não deve ser interpretada como um controle já implementado.

## 2. Ativos do sistema

| Ativo | Descrição e importância |
|---|---|
| Dados cadastrais dos usuários | Nome completo, nome de usuário e e-mail. São dados pessoais usados para identificar e contatar o titular. |
| Credenciais de acesso | Hash bcrypt das senhas e os mecanismos de autenticação. O hash não permite recuperar diretamente a senha, mas seu vazamento pode viabilizar tentativas de quebra offline. |
| Segredo do TOTP (2FA) | Chave usada para gerar e validar os códigos do segundo fator. A confidencialidade desse segredo é essencial para que o 2FA continue protegendo a conta. |
| Sessões autenticadas | Tokens opacos armazenados no banco e apresentados pelo navegador. Um token roubado pode permitir sequestro de sessão até expirar ou ser revogado. |
| Tokens de recuperação de senha | Tokens enviados por e-mail para redefinir a senha. São credenciais temporárias e devem ser protegidos contra leitura e reutilização. |
| Dados acadêmicos e de monitoria | Ofertas de monitoria, disciplinas, descrições e inscrições que relacionam usuários. Podem revelar interesses e vínculos acadêmicos. |
| Registros de auditoria | `security_logs` e `password_reset_logs`, usados para investigar autenticações e recuperações de senha. Sua integridade é necessária para rastreabilidade. |
| Banco de dados | Concentra dados pessoais, credenciais derivadas, sessões, tokens e relacionamentos. É um ativo crítico de confidencialidade, integridade e disponibilidade. |
| Servidor e configuração da aplicação | Código, `SECRET_KEY`, credenciais de banco e variáveis de configuração. O comprometimento pode afetar todos os demais ativos. |
| Serviço e conta de e-mail | Canal SMTP que entrega links de recuperação. O acesso à conta de e-mail pode permitir a redefinição de senhas. |
| Navegador e dispositivo do usuário | Mantêm o cookie de sessão e exibem QR codes e links de recuperação. Malware, extensões maliciosas ou compartilhamento do dispositivo podem expor esses dados. |

## 3. Ameaças e vulnerabilidades por ativo

| Ativo | Ameaças/vulnerabilidades relevantes | Impacto possível |
|---|---|---|
| Dados cadastrais e acadêmicos | Vazamento ou consulta indevida ao banco; credenciais administrativas excessivas; exposição em canal sem TLS. | Violação de privacidade, uso indevido de dados e descumprimento de princípios da LGPD. |
| Credenciais de acesso | Ataque de força bruta online; quebra offline caso o banco seja vazado; configuração insegura da aplicação. | Acesso indevido a contas e aos dados associados. |
| Segredo do TOTP | O campo `two_factor_secret` é armazenado em texto puro; acesso ao banco permite gerar códigos válidos. | Bypass do segundo fator e comprometimento da conta. |
| Sessões autenticadas | Interceptação do cookie em HTTP; roubo do token no dispositivo; uso de sessão não revogada. | Sequestro de sessão e acesso como outro usuário. |
| Tokens de recuperação | Interceptação do link; comprometimento da caixa de e-mail; exposição do token em logs ou histórico. | Redefinição não autorizada da senha. |
| Logs de auditoria | Alteração ou exclusão por usuário com privilégios excessivos; falta de registros para investigação. | Perda de evidência e dificuldade para detectar ou responder a incidentes. |
| Banco de dados | Vazamento, cópia não autorizada, indisponibilidade ou alteração maliciosa. | Comprometimento simultâneo de vários ativos e possível perda de integridade. |
| Servidor/configuração | `SECRET_KEY` possui fallback fraco e hardcoded; a variável não está no `.env.example`; `debug=True` é iniciado de forma fixa. | Falsificação de sessão, exposição de informações e, em cenário vulnerável, exploração do depurador. |
| Serviço de e-mail | Credenciais SMTP comprometidas; falha ou indisponibilidade do provedor; engenharia social. | Interceptação de recuperação de senha ou indisponibilidade do fluxo. |
| Navegador/dispositivo | XSS, malware, dispositivo compartilhado ou captura do QR code do 2FA. | Roubo de sessão, do segredo TOTP ou do token de recuperação. |

## 4. Matriz de riscos e contramedidas

| Risco | Ativos afetados | Nível | Contramedida existente | Situação |
|---|---|---:|---|---|
| Quebra de senhas por força bruta online | Credenciais | Alto | Após cinco falhas, a conta é bloqueada por 15 minutos; o contador fica persistido no banco. | Implementada |
| Quebra offline de hashes de senha | Credenciais, banco | Alto | Senhas são armazenadas com bcrypt, salt aleatório e fator de custo 12. | Implementada |
| Roubo ou reutilização de sessão | Sessões, dados pessoais | Alto | Sessões são tokens opacos armazenados no servidor, expiram em 30 minutos e podem ser revogadas no logout. O cookie usa `HttpOnly` e `SameSite=Lax`. | Parcial: `Secure` está desabilitado |
| Interceptação de credenciais e cookies em trânsito | Todos os dados enviados, sessões, tokens | Alto | Nenhuma proteção de transporte está configurada no código atual. | **Pendente: habilitar HTTPS/TLS, redirecionar ou bloquear HTTP e ativar `SESSION_COOKIE_SECURE` fora do desenvolvimento** |
| Comprometimento do segredo TOTP após vazamento do banco | Segredo do TOTP, contas | Alto | O TOTP é validado com janela de sincronização e há registro de eventos de segurança, mas isso não protege o segredo em repouso. | **Pendente: criptografar o segredo TOTP com uma chave separada e protegida** |
| Adivinhação ou vazamento de token de recuperação | Tokens, credenciais | Alto | Token gerado com CSPRNG, somente o hash SHA-256 é salvo, validade de 15 minutos e uso único com `used_at`. | Implementada |
| Acesso indevido por comprometimento do e-mail | Tokens, credenciais | Alto | Link é enviado ao endereço cadastrado por SMTP com STARTTLS; resposta genérica evita enumeração de contas. | Parcial: depende da segurança da conta e do provedor de e-mail |
| Adulteração de evidências | Logs de auditoria | Médio | A aplicação não oferece edição/exclusão e os scripts SQL restringem os logs a `SELECT` e `INSERT` para o role da aplicação. | Implementada quando os scripts de permissões são aplicados |
| Alteração de configurações e falsificação de sessão | Servidor, `SECRET_KEY`, sessões | Alto | A configuração é carregada por variáveis de ambiente, mas há fallback fraco para `SECRET_KEY`. | **Pendente: exigir `SECRET_KEY` forte e remover o fallback hardcoded** |
| Exploração do depurador em ambiente exposto | Servidor e todos os dados | Alto | Não há controle no código que condicione o debug ao ambiente. | **Pendente: remover `debug=True` fixo e permitir debug apenas por configuração explícita de desenvolvimento** |
| Exposição excessiva de dados pessoais | Dados cadastrais e acadêmicos | Médio | Consentimento obrigatório com finalidade e versão; consulta, exportação JSON e exclusão em cascata apoiam os direitos do titular. | Implementada |
| Exclusão incompleta de dados relacionados | Dados pessoais, sessões, monitorias | Médio | Chaves estrangeiras com `ON DELETE CASCADE` removem sessões, ofertas e inscrições relacionadas. | Implementada |
| Negação de serviço por bloqueio de conta | Contas | Médio | Bloqueio é temporário, evitando bloqueio definitivo provocado por terceiros. | Implementada |
| Comprometimento das credenciais SMTP | Serviço de e-mail, tokens | Alto | Credenciais são lidas de variáveis de ambiente e o transporte usa STARTTLS. | Parcial: exige proteção do ambiente e rotação das credenciais |

## 5. Plano de tratamento das pendências

As pendências de maior prioridade são:

1. **Comunicação segura:** disponibilizar HTTPS/TLS, rejeitar ou redirecionar
   HTTP e ativar a flag `Secure` dos cookies em ambientes não locais.
2. **Proteção do TOTP:** criptografar `two_factor_secret` em repouso, usando
   uma chave de aplicação separada da `SECRET_KEY` e armazenada fora do código.
3. **Segredos da aplicação:** remover o fallback de `SECRET_KEY`, exigir a
   variável no startup e documentá-la no `.env.example`.
4. **Modo de depuração:** impedir que o servidor seja executado com debug
   habilitado por padrão ou em ambiente exposto.

Enquanto essas ações não forem concluídas, o sistema deve ser tratado como
adequado apenas para desenvolvimento ou ambientes controlados, não como uma
implantação de produção com dados reais.

## 6. Referências

- [Arquitetura de autenticação e sessão](autenticacao.md)
- [Arquitetura de recuperação de senha](recuperacao-senha.md)
- [Conformidade com a LGPD](lgpd.md)
- [Proteção contra alteração dos logs](logs-imutaveis.md)
- [Mapeamento de dados pessoais](dados-pessoais.md)
