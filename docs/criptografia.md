# Criptografia e Comunicação Segura

Este documento descreve as estratégias de proteção implementadas na aplicação para garantir a confidencialidade e a integridade dos dados, tanto em trânsito quanto em repouso.

## 1. Dados em Trânsito (TLS/HTTPS)

A proteção dos dados enquanto trafegam entre o cliente e o servidor é fundamental para prevenir interceptações (ataques *Man-in-the-Middle*) e roubos de credenciais ou cookies de sessão.

### 1.1 Forçando Conexões Seguras
A aplicação Mentory exige a utilização do protocolo **HTTPS**.
- A flag `SESSION_COOKIE_SECURE` foi ativada por meio da variável de ambiente `SECURE_COOKIES=true`. Isso instrui o navegador a transmitir o cookie de sessão única e exclusivamente sobre conexões seguras.
- Adicionou-se uma camada de inspeção na entrada da aplicação (interceptador `before_request`). Se a variável ambiente exigir *cookies* seguros e a conexão for detectada como HTTP comum, a requisição é abortada e bloqueada com o código HTTP 403 (Forbidden), garantindo que dados confidenciais nunca sejam enviados em texto claro.

### 1.2 Certificados em Desenvolvimento e Produção
Para ambientes locais ou de desenvolvimento, a subida direta do Flask recebe o contexto SSL (Certificado `cert.pem` e chave `key.pem` autoassinados). Já em produção, espera-se que a aplicação seja servida por trás de um proxy reverso (como NGINX) que fará a terminação do TLS com certificados validados (ex: Let's Encrypt).

## 2. Dados em Repouso

As diretrizes de como os dados confidenciais são armazenados no banco de dados e no ambiente do servidor são parte crucial da estratégia de segurança.

### 2.1 Armazenamento de Segredos de Autenticação (TOTP)
A chave mestra geradora de códigos 2FA (`two_factor_secret`) é protegida no banco de dados usando criptografia simétrica com a biblioteca *Cryptography* (formato Fernet). O segredo em texto puro não fica legível em banco, mitigando o impacto em caso de vazamento da base de dados. O processo de cifrar/decifrar ocorre estritamente em memória usando a variável de ambiente `TOTP_ENCRYPTION_KEY`.

### 2.2 Proteção de Chaves de Criptografia
A separação de responsabilidades dita que as chaves de criptografia não devem residir junto com os dados protegidos nem serem *hardcoded* no código fonte:
- **`SECRET_KEY`**: A chave de assinatura das sessões Flask é provida via ambiente. A ausência dessa configuração impede a aplicação de iniciar.
- **`TOTP_ENCRYPTION_KEY`**: A chave usada para decifrar os segredos de 2FA dos usuários no banco também é isolada no arquivo `.env` fora do controle de versão.

---

Para revisar a análise de vulnerabilidades em relação à criptografia que levaram a estas implementações, consulte a nossa [Análise de Riscos](analise-riscos.md).
