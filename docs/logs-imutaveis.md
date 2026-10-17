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
4. aplica `app_role_setup.sql` e `log_permissions.sql`;
5. executa `validate_permissions.sql`;
6. inicia o backend com `DB_APP_USER` e `DB_APP_PASSWORD`.

Assim, a aplicação só inicia depois que o schema existe e os privilégios
mínimos foram aplicados. O PostgreSQL permanece no Docker quando o backend é
interrompido com `Ctrl+C`.

Os scripts SQL continuam separados em `backend/db` para auditoria, manutenção
e execução manual em ambientes que não utilizem o bootstrap local.

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
