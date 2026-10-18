# Proteção contra alteração dos logs de auditoria

Este projeto mantém os logs `security_logs` e `password_reset_logs` como **append-only**:

1. **Aplicação:** não existe rota para editar ou apagar registros de log.
2. **Banco de dados:** o role da aplicação recebe apenas `SELECT` e `INSERT` nessas tabelas.

Nas demais tabelas, o role da aplicação recebe somente as operações usadas pelo
backend. A restrição `append-only` é aplicada exclusivamente a
`security_logs` e `password_reset_logs`.

As sequências existentes recebem `USAGE` e `SELECT`, suficientes para os IDs
autogerados usados pelo backend. Objetos futuros não recebem grants
automaticamente: novas entidades devem ser adicionadas ao
`app_role_setup.sql` após revisão.

No `.env`, `DB_ADMIN_USER`/`DB_ADMIN_PASSWORD` são usados somente pelo
PostgreSQL e pelos scripts administrativos. A aplicação usa
`DB_APP_USER`/`DB_APP_PASSWORD`, que devem representar um usuário dedicado e
sem privilégios de administrador.

## Configuração automatizada

Não é necessário subir o servidor ou executar os SQLs manualmente. A partir da
raiz do projeto, configure o `.env` e execute:

```bash
bash setup.sh
```

O `setup.sh` executa, nesta ordem:

1. cria o ambiente virtual e instala as dependências Python;
2. sobe o PostgreSQL e aguarda a disponibilidade do banco;
3. executa `db.create_all()` com credenciais administrativas, usando os models;
4. valida os identificadores de banco (`DB_NAME`, `DB_ADMIN_USER`, `DB_APP_USER`, `DB_APP_ROLE`) e aplica `app_role_setup.sql` e `log_permissions.sql`;
5. executa `validate_permissions.sql`;
6. verifica se `SECURE_COOKIES` está ativo e gera certificados locais autoassinados (`cert.pem` e `key.pem`) via `gerar_certificados.sh` caso ainda não existam;
7. inicia o backend com `DB_APP_USER` e `DB_APP_PASSWORD`.

Assim, a aplicação só inicia depois que o schema existe e os privilégios
mínimos foram aplicados. O PostgreSQL permanece no Docker quando o backend é
interrompido com `Ctrl+C`.

Os scripts SQL continuam separados em `backend/db` para auditoria, manutenção
e execução manual em ambientes que não utilizem o bootstrap local.

## Segurança contra injeção de SQL no provisionamento

O provisionamento administrativo de roles e permissões segue controles estritos
para impedir interpolação insegura de SQL e exposição de credenciais:

1. **Validação prévia de identificadores:** tanto o `setup.sh` quanto os
   scripts `backend/db/app_role_setup.sql` e `backend/db/log_permissions.sql`
   validam que nomes de usuários, roles e banco seguem estritamente o padrão
   `^[a-zA-Z_][a-zA-Z0-9_]{0,62}$` antes de executar qualquer comando DDL/DCL,
   além de exigir identificadores distintos para `DB_ADMIN_USER`, `DB_APP_USER`
   e `DB_APP_ROLE`.
2. **Escape seguro de identificadores e literais:** comandos dinâmicos (`CREATE ROLE`,
   `ALTER ROLE`, `GRANT`) utilizam `format()` do PostgreSQL com `%I` para
   identificadores e `%L` para literais de senha, combinados com variáveis do
   `psql` (`:'variavel'` para literais e `:"variavel"` para identificadores) e
   `\gexec`, sem concatenação direta de strings SQL.
3. **Execução sem exposição de credenciais em logs:** o `psql` é executado com
   `--quiet` (`\set QUIET on`) e `--set ON_ERROR_STOP=1` (`\set ON_ERROR_STOP on`),
   garantindo interrupção imediata em caso de falha sem imprimir o conteúdo de
   `DB_APP_PASSWORD` ou `DB_ADMIN_PASSWORD` na saída padrão.
4. **Descontinuação de scripts locais legados (`setup_db.py`):** o script local
   `setup_db.py` (que utilizava interpolação de f-strings em Python) não faz
   parte da arquitetura do repositório e permanece bloqueado no `.gitignore`,
   sendo integralmente substituído pelo fluxo oficial (`setup.sh` +
   `backend/db/*.sql`).

## Validação manual esperada

Após aplicar os scripts, valide usando o usuário da aplicação. As tentativas de
alteração devem falhar:

```sql
UPDATE security_logs SET event_type = 'tampered' WHERE id = 1;
DELETE FROM password_reset_logs WHERE id = 1;
```

Para abrir uma sessão interativa, use `-it` e encerre com `\q`:

```bash
docker exec -it \
  -e PGPASSWORD="$DB_APP_PASSWORD" \
  projeto-integrador-postgres \
  psql -U "$DB_APP_USER" -d "$DB_NAME"
```

Erros esperados (ou equivalentes):

- `ERROR: permission denied for table security_logs`
- `ERROR: permission denied for table password_reset_logs`
