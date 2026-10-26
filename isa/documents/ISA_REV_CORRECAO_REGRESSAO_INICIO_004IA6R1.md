# ISA — Correção da regressão do Início

26/10/2026. O relato `ISA_REV_INICIO_INTEGRADO_004IA6.md` permanece como registro da 0.6.9. Esta nota corrige o que essa publicação não entregou na tela.

## O que voltou a responder

A consulta autenticada do Início voltou a ser montada. Em 0.6.9, `GET /api/home` quebrava no processo depois de ler a base, e o navegador mostrava “Não foi possível carregar suas informações. Nenhum valor foi gravado.” A 0.6.10 devolve a página no caminho WSGI. Isso foi verificado em PostgreSQL isolado e no navegador de laboratório, com pessoa sintética. Não houve sessão do proprietário, então a abertura pública autenticada continua por confirmar por ele.

## Causa da primeira falha

Nos logs `/ecs/isa` da tarefa publicada em 0.6.9, o pedido `/api/home` terminava assim:

`NameError: name 'environ' is not defined` em `wsgi_app.py`, dentro de `_route`, na linha que lia o mês da consulta.

`store.home` já tinha retornado. O erro não era sessão expirada, mês inválido, timeout, SQL nem desenho da tela. A resposta HTTP não saía. O cliente caía na mensagem genérica de carregamento. O botão **Tentar de novo** não explica essa primeira falha: a abertura chama `open()` sem evento.

## Defeitos secundários, corrigidos na mesma versão

- Repetir e dispensar uma leitura chamavam `open` direto. O clique ou a resposta da API podiam virar o mês. Mês fora do calendário agora responde 400, com a frase “O mês informado não é válido.” A repetição reenvia o mês já validado do período atual.
- Falha de transporte, contrato e desenho deixaram de compartilhar a mesma mensagem. A resposta só entra no cache depois de a estrutura mínima existir e o desenho concluir. O desenho que falha não é chamado de novo sobre o mesmo payload.
- O cache deixa de usar a pessoa de laboratório. A chave é a identidade da sessão, a conta, a moeda e o período. Saída, troca de pessoa e resposta atrasada de outro contexto descartam o estado. Sem cache dessa mesma chave, a tela mostra indisponibilidade, não zero e não o convite de primeiro acesso.
- O texto “Nenhum valor foi gravado” saiu. No erro, a área principal diz **Não conseguimos atualizar suas informações agora**, com **Tentar novamente**. Em 401, **Entrar novamente**. Importar e Registrar não aparecem como conserto da consulta.
- Importar extrato saiu do cabeçalho do Início. Continua em Lançamentos e no primeiro acesso real, depois de uma leitura vazia. Registrar fica na navegação: barra no desktop, menu inferior no celular, não nos dois e no conteúdo ao mesmo tempo.
- A leitura diária da ISA volta a poder ser pedida em segundo plano depois que os números já estão na tela, uma vez por identidade, conta, dia e impressão digital. O botão **Atualizar a leitura** continua. IA lenta não segura saldo, lista, calendário nem formulário.

## Integridade

A exceção acontecia depois da leitura. Não há, nesse log, indício de que o `GET` tenha apagado conta, movimento, saldo ou compromisso. A cópia anterior à imagem nova está em `backups/20261026T153237+0000/`, tarefa `a12e07867e8f43eb875e639917bebd7b`, saída 0, 31 tabelas, upload verificado. Não houve migration, seed, reset nem restauração por cima da base ativa.

Limite: não contei nem li lançamentos da conta real. A presença das tabelas na cópia não é uma auditoria linha a linha. A retirada de `sync_entries` da leitura de `/api/workspace` não foi revertida. O mês do Início lê movimentos e, à parte, lançamentos já materializados. Importação nova continua materializando ao final do lote. Não houve rotina sobre dados antigos, porque a falha observada não dependia disso e a lacuna de ocorrência sem movimento e sem lançamento não foi medida na base publicada.

## Composição

A imagem anterior à reformulação mostra Disponível, A pagar, Próxima entrada, O dinheiro chega?, Evolução, calendário, Ajuda da ISA e histórico. Ela é um estado sem valores e não prova saldos produtivos. A proposta 004IA6 continua sendo a direção: um período, dois terços para a consulta e um terço para a agenda. Não se voltou aos cartões soltos nem a dois controles de mês.

Na tela com dados sintéticos, essas funções ficaram assim: saldo, data e origem em **Situação do dinheiro**; compromissos e próxima entrada no mesmo mês; a decisão em **O dinheiro chega?**; o realizado em **Seu mês completo**; a trajetória em **Evolução**, quando o motor a calcula; a agenda e a ajuda da ISA na coluna lateral. O histórico separado “O que já aconteceu” não voltou.

## Prova

A reprodução da causa é o `GET /api/home` pelo aplicativo WSGI. Na 0.6.9 esse caminho gera o `NameError`. Na correção, `month=2026-10` responde 200 e `month=[object PointerEvent]` ou `2026-13` responde 400.

No PostgreSQL local `isa-pg-004p1`, o mesmo HTTP leu conta antiga sem saldo, compromisso parcial, compromisso sem data, lançamento manual, ocorrência importada, lote, natureza pendente, JSON inválido e duas moedas, sem 500. A conta isolada mostrou o manual e o importado; a visão de todas as moedas não os somou.

O cenário de 26/10/2026, também por HTTP e PostgreSQL, devolveu disponível R$ 1.200, falta em 28/10 de R$ 150, fechamento em 30/10 de R$ 1.350, reserva R$ 200 já incluída e margem de hoje R$ 0. A conta do Banco do Brasil isolada ficou em R$ 1.000. O resultado do mês não substituiu o saldo.

No navegador de laboratório, a pessoa sintética Paulo abriu o Início, recarregou, foi a Lançamentos e voltou, trocou o mês, repetiu depois de uma falha e a URL manteve `month=2026-10`, sem objeto de evento. Marina, sem esses dados, não viu o saldo de Paulo. As capturas preenchidas estão em `documents/reviews/inicio-004ia6r1/`, em 1440, 1280, 768, 390 e 360 px. O laboratório usa 16/10/2026 como hoje, então essa captura não é o cenário de 26/10; esse cenário está na prova HTTP.

O zoom real não foi aplicado: depois de Control+Equal no Chromium sem interface, `visualViewport.scale` continuou 1. Não se usou zoom de CSS no lugar disso.

Tempos no laboratório local, base sintética em SQLite, sete aberturas até **Situação do dinheiro**: p50 194 ms, p95 237 ms. Não é a rede publicada nem a base do piloto. A rota de IA atrasada não disparou nessa tela, porque não havia fato novo pedindo leitura. O botão manual estava na página e os números apareceram sem esperar IA.

## Publicação

https://isa.actionhub.com.br responde `isa-piloto 0.6.10`, oidc, postgres. `/api/ready` responde schema 9. `/api/workspace` e `/api/home` sem sessão respondem 401. O serviço `isa` está na task `isa-web:19`, rollout concluído. A imagem linux/amd64 é `sha256:eabd39c3e372a02670e4c937c18cc87c7717a457afb4113807f5adfc3da200d1`. O `home.js` servido traz a mensagem nova, a identidade da sessão e a leitura em segundo plano, e não traz “Nenhum valor foi gravado” nem `retry.onclick = open`. Cache-Control desses arquivos é `no-store`.

O ActionFinance permanece em `actionfinance-web:28`. Não houve ALB novo nem alteração de schema. O retorno da aplicação, se esta imagem precisar sair, é `isa-web:17`, versão 0.6.8, que abre o schema 9 sem apagar colunas. `isa-web:18` é a 0.6.9 e reproduz a falha. Não se restaura cópia antiga por cima da base.

Isto não é aceite do proprietário. Falta ele entrar e ver o próprio Início.
