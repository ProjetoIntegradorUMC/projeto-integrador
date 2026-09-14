# Mapeamento e minimização de dados pessoais do Mentory

## Objetivo

Este documento registra os dados pessoais coletados pelo Mentory, a finalidade de cada coleta e a justificativa de necessidade, conforme a regra de minimização de dados da LGPD.

## Dados pessoais coletados e justificativa

| Dado pessoal | Onde é coletado | Finalidade | Por que é necessário |
|---|---|---|---|
| Nome completo | Cadastro | Identificar o usuário na plataforma (quem é o monitor, quem é o mentorado) | Um sistema de conexão entre pessoas não funciona de forma anônima |
| Nome de usuário | Cadastro | Identificar a conta de forma única e exibir um identificador na plataforma | É usado para diferenciar contas e compor a identificação do usuário no sistema |
| E-mail | Cadastro | Login e canal de recuperação de senha | Único dado de contato coletado; usado só para autenticação e recuperação |
| Senha (armazenada como hash + salt) | Cadastro | Autenticar o usuário no login | Nunca fica em texto puro; só o hash irreversível é salvo |
| Segredo do 2FA (TOTP) | Ativação do 2FA no perfil | Gerar/validar o segundo fator no login | Só existe para quem ativa o 2FA por opção própria |
| Token de recuperação de senha | Solicitação de "Esqueci minha senha" | Permitir redefinir a senha com segurança | Temporário, expira em minutos e é invalidado após o uso |
| Registros de tentativas de login e de recuperação | Login e recuperação de senha | Detectar força bruta e auditar o processo | Exigência de segurança já prevista nas entregas do projeto |
| Data/hora e versão do consentimento | Cadastro (aceite dos termos) | Comprovar que o titular consentiu, e com qual versão dos termos | Exigência direta desta entrega |
| Disciplina oferecida ou buscada | Oferta de monitoria / inscrição | Conectar quem oferece ajuda numa disciplina com quem precisa dela | É a funcionalidade central do Mentory; sem esse dado o sistema de monitoria não existe |
| Registro do relacionamento (quem se inscreveu em qual monitoria de quem) | Inscrição em uma monitoria | Formalizar a conexão entre monitor e mentorado para que ambos acompanhem a monitoria | Necessário para o funcionamento básico da monitoria; ambas as partes precisam saber que estão conectadas |

## Dados explicitamente não coletados

A coleta do Mentory é limitada ao necessário. Os dados abaixo não constam do fluxo atual e, por isso, não são armazenados nem solicitados:

- CPF
- Telefone
- Endereço
- Data de nascimento
- Gênero
- Foto
- Papel de coordenação
- Matching automático, avaliação, reputação e agendamento

### Por que a coordenação fica de fora

O sistema atual não implementa uma funcionalidade de coordenação, nem qualquer requisito operacional que dependa de atribuir papel institucional ao usuário. Incluir esse dado sem uso concreto geraria coleta desnecessária e violaria o princípio de minimização previsto na LGPD.

## Verificação dos formulários

Conforme a análise do frontend atual, os fluxos principais do Mentory coletam apenas os dados necessários para a funcionalidade do sistema:

- Cadastro: nome completo, nome de usuário, e-mail, senha e aceite obrigatório dos termos. O aceite gera a data/hora e a versão do consentimento no backend.
- Oferta de monitoria: disciplina e descrição da oferta.
- Inscrição em monitoria: o relacionamento é registrado no contexto da inscrição, sem coleta de dado extra sobre a pessoa além do vínculo monitor/mentorado.

O campo de descrição da oferta é conteúdo operacional da monitoria, não um dado pessoal obrigatório do usuário. A caixa de aceite também não coleta um dado pessoal diretamente; ela registra os metadados de consentimento listados na tabela. A coleta de dados complementares (como foto, telefone, endereço, coordenação, avaliação e reputação) não faz parte do escopo atual e, portanto, não é necessária para a operação do Mentory nesta entrega.

## Conclusão

A coleta atual do Mentory está aderente ao princípio da minimização, pois cada dado solicitado tem finalidade clara, está associado a um fluxo relevante do sistema e não inclui campos que não são necessários para o funcionamento da plataforma.
