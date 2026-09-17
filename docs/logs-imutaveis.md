# Proteção contra alteração dos logs de auditoria

Este projeto mantém os logs `security_logs` e `password_reset_logs` como **append-only**:

1. **Aplicação:** não existe rota para editar ou apagar registros de log.
2. **Banco de dados:** o role da aplicação recebe apenas `SELECT` e `INSERT` nessas tabelas.

Nas demais tabelas e sequências do banco, o role da aplicação mantém todas as
permissões necessárias para o funcionamento do backend. A restrição
`append-only` é aplicada exclusivamente a `security_logs` e
`password_reset_logs`.

Todas as sequências do schema `public` recebem `USAGE`, `SELECT` e `UPDATE`,
pois o PostgreSQL exige essas permissões para inserir registros com IDs
autogerados. As permissões padrão também são configuradas para sequências
criadas posteriormente. Isso não permite alterar ou apagar linhas das tabelas.

No `.env`, `DB_ADMIN_USER`/`DB_ADMIN_PASSWORD` são usados somente pelo
PostgreSQL e pelos scripts administrativos. A aplicação usa
`DB_APP_USER`/`DB_APP_PASSWORD`, que devem representar um usuário dedicado e
sem privilégios de administrador.

## Pré-requisito de role/usuário dedicado da aplicação

Antes do script de proteção dos logs, crie (ou atualize) o usuário de aplicação
e associe-o a um role dedicado:

```bash
set -a
source .env
set +a

docker exec -i \
  -e PGPASSWORD="$DB_ADMIN_PASSWORD" \
  projeto-integrador-postgres \
  psql -v ON_ERROR_STOP=1 \
  -U "$DB_ADMIN_USER" \
  -d "$DB_NAME" \
  -v app_user="$DB_APP_USER" \
  -v app_password="$DB_APP_PASSWORD" \
  -v app_role="$DB_APP_ROLE" \
  < backend/db/app_role_setup.sql
```

Inicie a aplicação uma vez para que `db.create_all()` crie as tabelas. Depois
execute o script de permissões dos logs:

## Script de permissões dos logs (GRANT/REVOKE)

O script está em `backend/db/log_permissions.sql`.

Execute com o usuário administrador do PostgreSQL, informando o role usado pela aplicação:

```bash
docker exec -i \
  -e PGPASSWORD="$DB_ADMIN_PASSWORD" \
  projeto-integrador-postgres \
  psql -v ON_ERROR_STOP=1 \
  -U "$DB_ADMIN_USER" \
  -d "$DB_NAME" \
  -v app_role="$DB_APP_ROLE" \
  -v db_owner="$DB_ADMIN_USER" \
  < backend/db/log_permissions.sql
```

O role da aplicação recebe `USAGE` e `CREATE` no schema `public`, permitindo
que `db.create_all()` crie tabelas. As tabelas de log são então transferidas
para o administrador pelo segundo script; isso é necessário porque o dono de
uma tabela mantém permissão de alteração mesmo após um `REVOKE`.

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
