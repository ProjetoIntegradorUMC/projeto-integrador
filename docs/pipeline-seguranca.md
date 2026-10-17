# Segurança no Pipeline de CI/CD (GitHub Actions)

Este documento descreve as práticas de segurança adotadas nos fluxos de automação do Mentory (`.github/workflows/`), prevenindo ataques à cadeia de suprimentos (*Supply Chain Attacks*) e aplicando o Princípio do Menor Privilégio.

## 1. Princípio do Menor Privilégio (*Least Privilege*)

Por padrão, pipelines no GitHub Actions podem herdar permissões de leitura e escrita amplas no repositório. Para restringir a superfície de ataque:
- O nível global do arquivo de workflow declara `permissions: {}`, revogando todas as permissões padrão do token `GITHUB_TOKEN`.
- Apenas jobs específicos recebem permissões estritamente necessárias. No caso do job `release`, é concedida somente a permissão `contents: write` para criar e publicar a release e seus artefatos vinculados.

## 2. Fixação de Actions por SHA Imutável (*Pinning by SHA*)

Tags de versão Git (como `@v4` ou `@v4.2.2`) são referências mutáveis que podem ser alteradas ou sequestradas caso uma conta ou repositório de terceiro seja comprometido.
- Todas as actions externas utilizadas no projeto devem ser referenciadas pelo seu **commit hash SHA completo de 40 caracteres** (ex.: `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`).
- Um comentário deve acompanhar a referência indicando a versão legível correspondente (ex.: `# v4.2.2`).

## 3. Procedimento para Atualização de Actions

Quando for necessário atualizar uma action externa:
1. Acesse o repositório oficial da action (ex.: `github.com/actions/checkout`).
2. Consulte as *Releases* oficiais e selecione a versão desejada.
3. Obtenha o commit hash SHA exato correspondente ao commit daquela tag de release.
4. Atualize o arquivo de workflow substituindo o SHA antigo pelo novo e atualizando o comentário da versão.
5. Valide a execução do workflow em uma branch de teste antes de integrá-lo à `main`.
