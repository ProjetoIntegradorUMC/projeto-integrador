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
<<<<<<< Updated upstream
=======

## 4. Esteira DevSecOps Fundamental (`.github/workflows/devsecops-pipeline.yml`)

O workflow `devsecops-pipeline.yml` executa verificações automatizadas de segurança (*Shift-Left Security*) em cada `push` e `pull_request` direcionados à branch `main`, atuando como barreira preventiva antes da integração do código.

### 4.1 Varredura de Segredos no Histórico Git (`secrets-scan`)

Embora o repositório possua regras restritivas no `.gitignore` cobrindo arquivos sensíveis (`.env`, `.env.*`, `*.pem`, `*.key`), o job `secrets-scan` adiciona uma camada ativa de verificação no CI para impedir que credenciais como `SECRET_KEY`, `TOTP_ENCRYPTION_KEY`, chaves Fernet ou senhas do PostgreSQL sejam acidentalmente commitadas no histórico Git.

- **Ferramenta adotada:** [TruffleHog OSS](https://github.com/trufflesecurity/trufflehog) (`trufflesecurity/trufflehog@ea68ca03c865c5f324e86e849ced20ed3cf9dbbb # v3.99.8`).
- **Permissões do job:** `contents: read` (com `permissions: {}` declarado globalmente no workflow).
- **Escopo da análise:** O checkout é realizado com `fetch-depth: 0` (`actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2`), disponibilizando o histórico completo de commits para que o TruffleHog inspecione todas as alterações introduzidas no `push` ou no diff do `pull_request`.
- **Critério de bloqueio (`--only-verified` + `--fail` nativo):**
  - `--only-verified`: passado em `extra_args`, restringe os alertas a segredos e credenciais efetivamente verificáveis, reduzindo falsos positivos em dados simulados de testes automatizados.
  - `--fail`: injetado nativamente pela própria action `trufflesecurity/trufflehog`, instrui o TruffleHog a encerrar com código de saída diferente de zero (`exit code 183`) caso um segredo seja identificado, interrompendo o pipeline e bloqueando o merge do Pull Request.

### 4.2 Análise de Vulnerabilidades em Dependências - SCA (`sca-trivy`)

O arquivo `requirements.txt` declara as dependências Python do Mentory com versões fixas (como `Flask`, `Werkzeug`, `cryptography`, `bcrypt`, `SQLAlchemy` e `psycopg2-binary`). O job `sca-trivy` realiza a análise contínua de composição de software (*Software Composition Analysis* - SCA) para identificar vulnerabilidades públicas (CVEs) descobertas nessas bibliotecas ao longo do tempo.

- **Ferramenta adotada:** [Aqua Security Trivy](https://github.com/aquasecurity/trivy) (`aquasecurity/trivy-action@57a97c7e7821a5776cebc9bb87c984fa69cba8f1 # v0.35.0`), utilizando o binário oficial `v0.69.3` validado por checksum `SHA-256`.
- **Permissões do job:** `contents: read`.
- **Escopo da análise:** Executado em modo `fs` (*filesystem*, `scanners: vuln`) apontando para o diretório raiz do repositório (`scan-ref: .`), inspecionando o `requirements.txt` e quaisquer outros manifestos de pacotes presentes (ignorando diretórios locais como `.venv` e `node_modules`).
- **Critério de severidade e lógica de bloqueio:**
  - `severity: HIGH,CRITICAL`: filtra exclusivamente vulnerabilidades de severidade Alta ou Crítica catalogadas em bases de CVEs.
  - `exit-code: '1'`: faz o step retornar erro e bloquear o merge caso sejam encontradas vulnerabilidades que atendam ao critério de severidade. Na implantação inicial do job, o Trivy detectou CVEs de severidade Alta na biblioteca `cryptography` (incluindo `CVE-2026-40247`, `CVE-2026-40249` e `GHSA-5379-gmf8-6ccf`), bloqueando a PR até a atualização da dependência para `cryptography==50.0.0` no `requirements.txt`.
  - `ignore-unfixed: true`: suprime CVEs que ainda não possuem versão corrigida disponibilizada pelos mantenedores da biblioteca, evitando falsos bloqueios da esteira quando não há atualização aplicável.
- **Artefato de auditoria (`trivy-sca-report`):** Ao término da varredura (mesmo em caso de falha, graças à condição `if: always()`), o relatório JSON (`trivy-sca-report.json`) é publicado na aba Actions via `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2` sob o nome `trivy-sca-report`.
>>>>>>> Stashed changes
