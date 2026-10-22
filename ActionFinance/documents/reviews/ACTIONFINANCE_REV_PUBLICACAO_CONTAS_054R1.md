# ACTIONFINANCE_REV_PUBLICACAO_CONTAS_054R1

22/10/2026. Fechamento e publicação da jornada de contas do Prompt 054. A primeira etapa ficou registrada em [ACTIONFINANCE_REV_DADOS_CONTAS_054.md](ACTIONFINANCE_REV_DADOS_CONTAS_054.md) e não publicou. Esta etapa publica no serviço existente do ActionFinance. A ISA e a Spider não foram alteradas.

## Onde está

https://actionfinance.actionhub.com.br devolve a versão **0.2.11**. O caminho é Tesouraria → Contas → Abrir → **Dados da conta**.

Saúde pública `GET /actuator/health` respondeu 200. A task em execução está `HEALTHY`. `GET /api/v1/financial-accounts` sem sessão respondeu 401. O HTML servido aponta para `index-Dd2g04DF.js` e `index-DdIcnaWp.css`. Esse JavaScript contém “Dados da conta”, “Complete os dados desta conta” e “Conexão automática ainda não disponível”, e não contém “Gerenciar conta”.

Não houve sessão autenticada de produção nesta verificação. A prova autenticada foi a do laboratório isolado. O aceite do proprietário continua distinto.

## Versão e código

Commit da candidata: `5be64152` em `feat/actionfinance-extrato-032`, remoto `https://github.com/oscarsarquis-max/leaction-ecosystem.git`. A versão pública antes desta troca era 0.2.10, task `actionfinance-web:27`, Flyway desligado.

Imagem linux/amd64 publicada: `253137917703.dkr.ecr.us-east-2.amazonaws.com/actionfinance@sha256:f4fe545976b6dded0c9a3c4cab0d16c4eefcac21c077230ce3851505d0edf208`. O índice enviado ao registry é `sha256:60d71a2433790d34aa40edd50e607ecc413d4ce7f8e3251902b415c17663c07a`; a task usa o manifesto amd64. O JAR da imagem contém `V25__account_registration.sql` e `index-Dd2g04DF.js`.

Task web: `actionfinance-web:28`. Flyway permanece `false`. Rollout `COMPLETED`, uma task em execução. A imagem de retorno da aplicação é a 0.2.10, `actionfinance-web:27`, `sha256:4c5b3c11f09252887ba4e5a968771aef46617a597f15f77b4e522c6d05ced065`. Reverter a task não remove colunas. A escrita antiga altera nome e situação e não grava as colunas novas nem os contatos, então não apaga identificação já preenchida. Não houve ensaio da imagem antiga contra o schema V25 em produção.

## Backup e migration

Snapshot RDS `actionfinance-pre-v25-20261022`, criptografado, status `available`, progresso 100, início `2026-10-22T15:47:59Z`. É cópia da instância `actionfinance` antes da V25.

O histórico Flyway lido antes da mudança tinha as versões 1 a 24 com sucesso. A V25 não estava aplicada. A task única `actionfinance-migrate:7`, com a imagem nova e Flyway ligado, validou 25 migrations, aplicou somente a V25 e parou em v25. A task foi encerrada depois disso. Checksum registrado da V25: `318546030`. Nenhum repair.

Indicadores antes e depois: 1 conta, 0 títulos, 0 baixas, soma de baixas 0, 0 movimentos, soma de movimentos 0, 1 vínculo de origem, 6 lotes de extrato, 0 linhas. Depois da V25 a conta segue com instituição nula e há 0 contatos. Nada foi preenchido na conta existente, nenhum saldo foi criado e nenhum movimento foi reatribuído.

## Prova no laboratório

Postgres isolado, sem usar a base local da porta 5439 nem a base de produção. Empresa sintética Padaria Exemplo.

A conta antiga abre em Dados da conta, com Não informado e Complete os dados desta conta. A edição gravou banco, número `0012345-6` e modalidade, manteve o número mascarado até Mostrar número, e deixou a posição Não apurada. O contato foi incluído, editado e continuou na aba depois de reabrir. Quem só consulta vê os dados e não recebe Editar dados nem Salvar. O caixa físico criado no diálogo de recebimento não pede banco e o diálogo fecha com a conta selecionada. Movimentações preserva Não apurada sem saldo inicial e zero quando o zero foi registrado. Acesso e importação declara a conexão automática indisponível, sem botão de conectar. Ver extrato e voltar preserva a conta e a aba.

Larguras medidas: 1440 com colunas 891 e 446 (cerca de dois terços), 1280 com 785 e 392, 768, 390 e 360 empilhadas, sem rolagem horizontal da página. Título 28 px no desktop e 24 px em 390 e 360. Obrigatório ausente foca o banco. E-mail opcional inválido abre Mais informações, mostra o erro e foca o campo. Resposta perdida mantém o rascunho e a nova tentativa grava uma conta. Conflito de versão mantém o rascunho e pede conferência. Capturas em `documents/reviews/screenshots/prm-054r1/`.

O comando de zoom do navegador, Control+= e depois teclado numérico, deixou `visualViewport.scale` em 1, a largura em 1440 e o título em 28 px. A captura `zoom-200.png` registra essa tentativa. Não foi usada transformação CSS no lugar do zoom.

O teste `retries a create with the same key after a lost transport response` falhava porque o texto da descrição aparecia no título e de novo nos dados. A asserção passou a usar o título de nível 1. A verificação de chave e corpo idempotentes permanece. A suíte filtrada dessa jornada passou.

Antes da publicação, criar conta nova respondia 500: o insert tinha 22 marcadores e 23 valores. O marcador que faltava foi incluído e o caixa do diálogo de baixa passou a gravar.

## Limites

Conexão automática continua indisponível. Não há sessão autenticada de produção nesta prova. O aceite não está atribuído. O resumo da Tesouraria não mudou. Investimento continua sendo modalidade de cadastro.
