# Evidências de TLS/HTTPS e Bloqueio de Conexões HTTP em Produção

Este documento apresenta a fundamentação arquitetural e as evidências operacionais coletadas contra o ambiente de produção (`https://mentory.stack-n8n.cloud`) para comprovar:
1. A restrição de confiança no cabeçalho `X-Forwarded-Proto` exclusivamente ao proxy reverso **Traefik v2.11** (através de isolamento de rede Docker e `ProxyFix`).
2. O bloqueio de conexões HTTP não criptografadas (tanto na borda do proxy quanto na camada de aplicação Flask).
3. A proteção do tráfego em trânsito por **TLS 1.3** com cadeia de certificados válida emitida pela **Let's Encrypt** (`certresolver=myresolver`).

---

## 1. Modelo de Confiança do `X-Forwarded-Proto` e Isolamento de Redes Docker

Em [`docker-compose.prod.yml`](../docker-compose.prod.yml), a topologia de rede de produção opera com duas barreiras complementares que impedem a falsificação (*spoofing*) do cabeçalho `X-Forwarded-Proto`:

1. **Ausência de exposição da porta 5000 no host e isolamento entre redes (`mentory-internal` e `n8n-stack_proxy`):**
   - O serviço `mentory-web` (Gunicorn + Flask na porta interna `5000`) **não declara a diretiva `ports:`** no `docker-compose.prod.yml`. Portanto, a porta `5000` não é publicada na interface pública da VPS (`72.62.106.100`).
   - A rede `mentory-internal` é declarada com `internal: true`, isolando a comunicação entre `mentory-web` e `mentory-postgres` sem acesso externo.
   - A única conexão com a borda ocorre pela rede Docker `n8n-stack_proxy` (`external: true`), onde reside o container do proxy reverso **Traefik v2.11**. Nenhum cliente externo na internet consegue enviar pacotes TCP diretamente para `mentory-web:5000` contornando o Traefik.

2. **Validação estrita de salto único com `ProxyFix(x_for=1, x_proto=1)` e `enforce_https()`:**
   - Em [`backend/app/__init__.py`](../backend/app/__init__.py), a aplicação envolve o servidor WSGI com `ProxyFix(app.wsgi_app, x_for=1, x_proto=1)` (`werkzeug.middleware.proxy_fix`).
   - O parâmetro `x_proto=1` determina que o Flask confie exclusivamente no **último salto (1 hop)** adicionado pelo proxy reverso imediato (Traefik), descartando quaisquer valores de `X-Forwarded-Proto` que um cliente mal-intencionado tente enviar antes do Traefik.
   - No hook `@app.before_request` (`enforce_https()`), quando `SECURE_COOKIES=true` e `not request.is_secure`, a requisição é imediatamente recusada com `HTTP 403 Forbidden` (`"Acesso negado. A aplicação exige conexão segura (HTTPS)."`).

---

## 2. Evidência Operacional de Bloqueio de HTTP em Produção (`curl`)

### 2.1 Bloqueio na borda (Porta 80 / Traefik v2.11)
Como o roteador do Mentory no `docker-compose.prod.yml` está vinculado exclusivamente ao entrypoint HTTPS (`traefik.http.routers.mentory.entrypoints=websecure`, `traefik.http.routers.mentory.tls=true`), o Traefik não aceita roteamento em texto claro na porta 80 para `mentory.stack-n8n.cloud`, rejeitando requisições HTTP imediatamente na borda antes mesmo de alcançarem o container `mentory-web`:

```text
$ curl -v http://mentory.stack-n8n.cloud
* Host mentory.stack-n8n.cloud:80 was resolved.
* IPv6: (none)
* IPv4: 72.62.106.100
*   Trying 72.62.106.100:80...
* Established connection to mentory.stack-n8n.cloud (72.62.106.100 port 80) from 192.168.18.122 port 34676 
* using HTTP/1.x
> GET / HTTP/1.1
> Host: mentory.stack-n8n.cloud
> User-Agent: curl/8.18.0
> Accept: */*
> 
* Request completely sent off
< HTTP/1.1 404 Not Found
< Content-Type: text/plain; charset=utf-8
< X-Content-Type-Options: nosniff
< Date: Tue, 17 Nov 2026 14:21:27 GMT
< Content-Length: 19
< 
404 page not found
* Connection #0 to host mentory.stack-n8n.cloud:80 left intact
```

### 2.2 Bloqueio na camada de aplicação (`HTTP 403 Forbidden` em `enforce_https()`)
Caso uma requisição HTTP sem terminação TLS (ou com salto final `X-Forwarded-Proto: http`) chegue à porta interna `5000` do container `mentory-web` com `SECURE_COOKIES=true`, o middleware `ProxyFix(x_for=1, x_proto=1)` mantém `request.is_secure = False` e o interceptador `enforce_https()` bloqueia o acesso com `HTTP/1.1 403 Forbidden`:

```text
$ docker compose -f docker-compose.prod.yml exec -T mentory-web curl -v http://127.0.0.1:5000/
*   Trying 127.0.0.1:5000...
* Connected to 127.0.0.1 (127.0.0.1) port 5000
> GET / HTTP/1.1
> Host: 127.0.0.1:5000
> User-Agent: curl/8.14.1
> Accept: */*
> 
< HTTP/1.1 403 FORBIDDEN
< Server: gunicorn/23.0.0
< Content-Type: text/html; charset=utf-8
< X-Content-Type-Options: nosniff
< X-Frame-Options: DENY
< Referrer-Policy: strict-origin-when-cross-origin
< Strict-Transport-Security: max-age=31536000; includeSubDomains
< 
<!doctype html>
<html lang=en>
<title>403 Forbidden</title>
<h1>Forbidden</h1>
<p>Acesso negado. A aplicação exige conexão segura (HTTPS).</p>
```

---

## 3. Evidência Operacional de Tráfego Cifrado e Cadeia Let's Encrypt (`openssl s_client`)

Saída real do comando `openssl s_client -connect mentory.stack-n8n.cloud:443 -servername mentory.stack-n8n.cloud </dev/null`, comprovando:
- Certificado emitido por **Let's Encrypt (`C=US, O=Let's Encrypt, CN=YR1`)** até a raiz **ISRG Root X1**.
- Protocolo negociado **TLSv1.3** com cifra `TLS_AES_128_GCM_SHA256`.
- Validação completa da cadeia com **`Verify return code: 0 (ok)`**.

```text
$ openssl s_client -connect mentory.stack-n8n.cloud:443 -servername mentory.stack-n8n.cloud </dev/null
Connecting to 72.62.106.100
CONNECTED(00000003)
depth=3 C=US, O=Internet Security Research Group, CN=ISRG Root X1
verify return:1
depth=2 C=US, O=ISRG, CN=Root YR
verify return:1
depth=1 C=US, O=Let's Encrypt, CN=YR1
verify return:1
depth=0 CN=mentory.stack-n8n.cloud
verify return:1
---
Certificate chain
 0 s:CN=mentory.stack-n8n.cloud
   i:C=US, O=Let's Encrypt, CN=YR1
   a:PKEY: RSA, 4096 (bit); sigalg: sha256WithRSAEncryption
   v:NotBefore: Oct 18 13:22:47 2026 GMT; NotAfter: Jan 16 13:22:46 2027 GMT
 1 s:C=US, O=Let's Encrypt, CN=YR1
   i:C=US, O=ISRG, CN=Root YR
   a:PKEY: RSA, 2048 (bit); sigalg: sha256WithRSAEncryption
   v:NotBefore: Sep  3 00:00:00 2025 GMT; NotAfter: Sep  2 23:59:59 2028 GMT
 2 s:C=US, O=ISRG, CN=Root YR
   i:C=US, O=Internet Security Research Group, CN=ISRG Root X1
   a:PKEY: RSA, 4096 (bit); sigalg: sha256WithRSAEncryption
   v:NotBefore: May 13 00:00:00 2026 GMT; NotAfter: Sep  2 23:59:59 2032 GMT
---
subject=CN=mentory.stack-n8n.cloud
issuer=C=US, O=Let's Encrypt, CN=YR1
---
No client certificate CA names sent
Peer signing digest: SHA256
Peer signature type: rsa_pss_rsae_sha256
Negotiated TLS1.3 group: X25519MLKEM768
---
SSL handshake has read 6219 bytes and written 1629 bytes
Verification: OK
---
New, TLSv1.3, Cipher is TLS_AES_128_GCM_SHA256
Protocol: TLSv1.3
Server public key is 4096 bit
This TLS version forbids renegotiation.
Compression: NONE
Expansion: NONE
No ALPN negotiated
Early data was not sent
Verify return code: 0 (ok)
---
```
