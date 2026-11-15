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

### 2.3 Rotação da Chave `TOTP_ENCRYPTION_KEY`

A rotação periódica ou emergencial (em caso de suspeita de comprometimento) da variável `TOTP_ENCRYPTION_KEY` exige cuidado operacional porque os segredos armazenados na coluna `users.two_factor_secret` estão cifrados com a chave vigente no momento do cadastro do 2FA.

#### Impacto da troca direta sem migração
- **Falha na decifragem (`InvalidToken`):** Em `backend/app/two_factor.py`, a função `decrypt_totp_secret()` utiliza `Fernet(key).decrypt(...)`. Se o valor de `TOTP_ENCRYPTION_KEY` for simplesmente substituído no `.env` sem recifrar os registros existentes, qualquer leitura de um usuário com `two_factor_enabled=True` lançará `InvalidToken` (convertido em `RuntimeError("Não foi possível decifrar o segredo TOTP armazenado")`), bloqueando o login e a validação de 2FA desses usuários até que o segundo fator seja reconfigurado.
- **Cache em memória (`@lru_cache`):** A função `get_totp_fernet()` mantém a instância `Fernet` em cache (`@lru_cache(maxsize=1)`) durante todo o ciclo de vida do processo. Qualquer alteração de chave exige reinicialização dos workers da aplicação para entrar em vigor.

#### Procedimento seguro de rotação
Para rotacionar `TOTP_ENCRYPTION_KEY` sem indisponibilidade ou perda de acesso dos usuários com 2FA ativo:

1. **Gerar a nova chave Fernet** em ambiente seguro (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
2. **Transição com `MultiFernet` (sem downtime) ou recifragem administrativa:**
   - **Abordagem recomendada (`MultiFernet`):** Configurar temporariamente `MultiFernet([Fernet(NOVA_CHAVE), Fernet(CHAVE_ANTIGA)])`. Nessa configuração, o `MultiFernet` decifra segredos antigos usando `CHAVE_ANTIGA` e cifra novos registros (ou atualiza tokens existentes via `.rotate()`) exclusivamente com `NOVA_CHAVE`.
   - **Abordagem por script administrativo:** Executar uma rotina de manutenção que leia cada registro não nulo de `users.two_factor_secret`, decifre em memória com `CHAVE_ANTIGA`, cifre imediatamente com `NOVA_CHAVE` e persista o novo token no banco dentro de uma transação.
3. **Atualizar o ambiente e reiniciar workers:** Substituir `TOTP_ENCRYPTION_KEY` pela `NOVA_CHAVE` no arquivo `.env` de produção e reiniciar os containers/workers da aplicação para invalidar o `@lru_cache` de `get_totp_fernet()`.
4. **Revogar a chave antiga:** Após validar que todos os registros foram migrados e que a autenticação 2FA opera normalmente com a nova chave, remover `CHAVE_ANTIGA` do ambiente e de quaisquer cofres temporários.

---

Para revisar a análise de vulnerabilidades em relação à criptografia que levaram a estas implementações, consulte a nossa [Análise de Riscos](analise-riscos.md).
