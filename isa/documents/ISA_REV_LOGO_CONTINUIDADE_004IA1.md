# ISA 0.6.1 — logo e continuidade dos dados

17/10/2026. Código `9a756d95`.

O arquivo solicitado é `images/logoisantrans.png`, com fundo azul opaco. Ele foi copiado sem alteração para `prototype/logoisantrans.png`. O cabeçalho comum passou a exibi-lo em todas as páginas da aplicação, incluindo entrada, Início, registro, lançamentos, importação, planejamento e Perfil. O link da marca leva ao Início. A imagem tem texto alternativo e enquadramento compacto por CSS, sem modificar o arquivo original.

A mesma imagem foi aplicada ao cliente de acesso do diretório Cognito `isa`, preservando o CSS e as configurações de autenticação. O login publicado foi aberto sem informar credenciais e mostrou a nova imagem.

## Continuidade

O proprietário esclareceu que os registros do piloto são dados reais de produção e precisam permanecer após o piloto. A diretriz foi registrada em `documents/ISA_CONTINUIDADE_PRODUCAO.md` e em `AGENTS.md`. Não há prazo de descarte por fim do piloto. A retenção de sete dias das cópias não é expiração dos dados ativos.

Esta atualização não tem migration, carga, limpeza, criação de usuário ou alteração de registro financeiro. O schema permanece 4. Banco, identidades, permissões de IA e rotina de backup permanecem os existentes. O Finance continua em `actionfinance-web:27`.

## Validação e publicação

A sintaxe de `app.js` passou. A imagem foi verificada dentro do pacote, com resposta 200 e `Content-Type: image/png`. No navegador local, a marca carregou com 2.000 pixels de largura original. Na emulação de 390 px, o documento também mediu 390 px; a marca mediu 253,75 × 76,125 px, sem rolagem horizontal.

O host público respondeu versão `isa-piloto 0.6.1`, saúde 200, `ai=claude-bedrock`, readiness 200 com schema 4, e IA sem sessão em 401. A mudança usa a task `isa-web:9`. Imagem por digest do índice: `sha256:3ee77c33191c0d1620ac78132d9642b8eb6d0be550f1a3051133cad0efbd06af`. Manifesto linux/amd64: `sha256:8007658b6aa9e775552691fd1173947b7d5a94c7182d441f4c571c47f86c9988`.

Retorno da aplicação: `isa-web:8`, versão 0.6.0. A cópia diária permanece em `isa-backup:5`, que já inclui a fila e o histórico de IA. Não houve operação na base financeira.

Conferência final: rollout COMPLETED, uma tarefa e nenhuma pendente. A página pública foi recarregada e mostrou o logo com fundo azul. Captura: documents/prototipo/logo-publicado-0.6.1.jpg.
