# projeto-integrador

## Release

O workflow em `.github/workflows/release.yml` cria uma release ao enviar uma tag no formato `v*`.

Fluxo:

```bash
# abrir PR e mergear na main

git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Importante:

- não faça commit direto na `main`;
- a tag precisa começar com `v` (ex.: `v1.2.3`);
- o workflow gera o ZIP da aplicação e cria a release no GitHub automaticamente.
