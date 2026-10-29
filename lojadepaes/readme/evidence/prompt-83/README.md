# Prompt 83 — Piloto especializado publicado e ativo

07/10/2026. Autorização do proprietário nesta tarefa: publicar o piloto, não degustação nem certificação. Revisão técnica/editorial: `agente-revisao-assistida`. Sem parceria Evino, sommelier, assinatura do proprietário ou «Escolha de A Loja».

## Produção efetiva

| Peça | Valor |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007f` |
| Bundle | `/assets/index-B1tJLCHz.js` |
| Alembic | `d1a6e3b15c82` (aditivo: `c9f5d2e04a71` → `d1a6e3b15c82`) |
| Flag especializada | `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true` no runtime do container |
| Flags preservadas | Gigio comum on; vitrine pública on; complementos do Gigio on |
| Regras | `83` |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

A imagem `e` subiu primeiro com a flag ainda desligada, recebeu o upsert e só então ligou a flag. A `f` corrige o anexo de fonte fora do escopo (ver abaixo). Health sozinho não prova fundamentação.

Backup no host: `/opt/lojadepaes/backups/lojadepaes-20261007T170420Z.sql.gz` e `…171446Z.sql.gz`. Sem cópia do banco local e sem seed comercial global.

## Referências publicadas (somente estas)

| Chave | Estado | Fonte | Revisor |
|---|---|---|---|
| `wine-churrasco-porco` | published · pairing · verified · v2 | https://www.evino.com.br/blog/vinhos-e-churrasco/ (18/01/2026) | `agente-revisao-assistida` |
| `wine-queijo-tabua` | published · pairing · verified · v2 | https://www.evino.com.br/blog/vinhos-e-queijos-como-harmonizar/ (05/02/2026) | `agente-revisao-assistida` |

`loja_choice=false` em todas. URLs e localizadores reconfirmados nesta sessão (artigos acessíveis).

## Fora da recuperação

| Chave | Estado |
|---|---|
| `wine-dao-leitao` | draft · excluded · inaccessible |
| `wine-pairing-per-product` | draft · excluded · pending |
| `cheese-canastra-ig` | draft · informational · verified (registro, não harmonização) |
| `oil-azeite-brasileiro-embrapa` | draft · excluded · inaccessible |

## Prova real (API servida, Bedrock)

Conversas genéricas, sem dados de cliente. JSON em `prod/`.

| Pergunta | Fonte no payload | CTA |
|---|---|---|
| Churrasco de porco e linguiça | só Evino churrasco; locator de suínos/linguiça; `loja_choice` false | `/acompanhar?cats=vinhos&mesa=porco&ids=…` com três ofertas reais do Hub |
| Tábua de queijos | só Evino queijos; brancos / brut / Chardonnay | vitrine com ids reais de vinhos e queijos |
| Leitão + vinho do Dão (fora do escopo) | **nenhuma** fonte especializada depois da `f` | vitrine de acompanhamentos, sem alegar consulta do Dão |

No `e`, a pergunta do leitão anexou indevidamente a fonte da tábua (o modelo pediu a ferramenta com outro `q`, e a resposta citou queijo). Artefato: `prod/chat-out-e-leak.json`. A `f` só devolve fonte se a **pergunta do cliente** sustentar a referência. Prova pós-correção: `prod/chat-out.json` (`sources: []`) e `prod/chat-pork-f.json` (fonte do churrasco intacta).

O Gigio ainda pode dar orientação geral sobre Dão; isso não é consulta especializada. Canastra/Embrapa/método não apareceram como fonte.

## Prova isolada

`tests/test_prompt82.py` + `test_prompt81.py`: 31 passed. Inclui publicação só das duas chaves e recusa de fonte forçada.

## Navegador servido

O chat headless estourou o tempo (mesmo limite já visto no Prompt 80). A fundamentação da conversa é a API ao vivo. O site servido foi aberto para layout e regressão:

| Captura | O quê |
|---|---|
| `prod/gigio-open-1440.png` / `390.png` | painel do Gigio, campo e atalhos |
| `prod/vitrine-pork-cta-1440.png` / `390.png` | CTA real do churrasco; garrafas inteiras em `contain`; 3/1 colunas |
| `prod/vitrine-cheese-cta-1440.png` | CTA da tábua; itens do Hub, sem selo de IG |
| `prod/vitrine-preserved-*.png` | mesa leitão/salada do Prompt 80 |
| `prod/vitrine-geral-1440.png` | catálogo geral, grade 3, 12/página |
| `prod/order-review-no-submit.png` | `/pedido/novo` vazio; nada enviado |

A palavra «Canastra» em anúncio do Hub continua não sendo a IG nem harmonização. Fonte de estilo não certifica SKU. Sem e-mail, pedido, compra ou cobrança.

## Rollback (sem restaurar banco antigo)

1. Só a camada especializada: `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=false` e recreate da API. Chat, vitrine, pedidos e pagamentos permanecem.
2. App anterior ao piloto: `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007d`. A tabela de referências pode ficar; a `d` a ignora.
3. Não restaurar dump sobre vendas.

SSH desta sessão: timeout em `:22` até o runbook Lightsail liberar só o IP de saída `/32` (`191.57.224.95/32`). Sem porta aberta ao mundo.
