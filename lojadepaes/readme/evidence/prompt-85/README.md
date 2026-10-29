# Prompt 85 — Restaurar o acesso aos acompanhamentos na conversa do Gigio

07/10/2026. Incremento depois do Adendo 84A (`prod-20261007i`). Sem refazer a base 84/84A. Sem migração. Revisão técnica: `agente-revisao-assistida`. Sem pedido, pagamento ou e-mail real.

## Produção efetiva

| Peça | Valor |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007k` (rollback de app: `prod-20261007j`; não usar `h`) |
| Bundle | `/assets/index-Demy9U2N.js` |
| Alembic | `f3c9a1b28e04` — sem mudança |
| Flag especializada | `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true` |
| Flags preservadas | Gigio comum on; vitrine pública on; complementos on |
| Regras | `85` |
| Timeout Hub | 4 s (antes 2 s) |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Backup no host: `/opt/lojadepaes/backups/lojadepaes-20261007T205748Z.sql.gz`. Sem cópia do banco local e sem seed comercial.

## Causa comprovada

A captura do proprietário tinha fonte Wine Folly («Sardinhas e peixes de sabor intenso»), link «Pairing Wine with Fish» e receita «Sardinhas e Homus…», sem o botão comercial. Isso prova a ausência da ação, não a causa.

Rastreio no código e na produção:

1. **Inferência da mesa.** «O que combina…» não era `TABLE_ASK`. Sem essa âncora, os complementos da refeição (azeites da sardinha) só apareciam se o modelo dissesse «azeite». Corrigido em `j`.
2. **Filtro especializado antes do recorte.** `select_contextual_cards` (3 por categoria) rodava antes da correspondência Wine Folly e descartava Cava/Lambrusco. Corrigido em `j`: filtra o conjunto completo e só depois recorta.
3. **Snapshot do Hub incompleto tratado como «sem produto».** Depois do `j`, a Loja serviu 19 itens (espumantes, queijos, frios) **sem azeites**, enquanto o Hub já tinha a prateleira `azeites` (Serra Morena, Serrata, Fátima, etc.). Cache de 300 s + primeira leitura incompleta. A API devolveu «Explorar a vitrine» + aviso de ausência — honesto quanto à seleção, mas **indisponibilidade técnica apresentada como falta de correspondência**. Corrigido em `k`: TTL 45 s; se a consulta pede uma categoria que o snapshot não tem, a Loja relê o Hub; prateleira do Hub com ofertas que a Loja descartou não entra no cache.

Não foi cache do modelo, nem falta de estoque inventada, nem alargamento do filtro Wine Folly. Espumante genérico continua sem valer por Champagne; rosé genérico não vale por rosé seco.

## Regras da ação comercial (servidor)

| Situação | Botão |
|---|---|
| Estilo sugerido + ofertas compatíveis | **Ver acompanhamentos sugeridos** |
| Rótulo avaliado disponível | o mesmo, com identidade/safra |
| Rótulo avaliado ausente + alternativas | **Ver alternativas para esta combinação** (sem herdar nota) |
| Nenhuma oferta compatível | orientação + **Explorar a vitrine** (genérico) |
| Hub falhou | resposta e fontes; aviso «A consulta aos acompanhamentos não foi concluída.» |

A URL vem do servidor (`gigio_lookup` + `infer_suggested_query`). Fonte e receita não substituem o botão.

## Critérios da sardinha

Fonte: Wine Folly, *Pairing Wine with Fish*, grupo de peixe intenso. Hints de vinho: `lambrusco`, `pinot noir`, `gamay`, `cava`. Receita publicada: `/receitas/sardinhas-e-homus-de-grao-de-bico-fresco-tartine-bread`. Complemento da mesa: azeites.

No Hub ao vivo **não** havia Cava, Lambrusco, Pinot Noir nem Gamay com atributo. Os azeites portugueses extra virgem **sim**. A seleção sugerida da sardinha é de azeites, não de vinho branco automático nem de espumante genérico.

## Perguntas usadas (reprodução, não a mensagem original da captura)

| Pergunta | Fonte | CTA / ofertas |
|---|---|---|
| O que combina com a receita de sardinhas com homus de vocês? | Wine Folly sardinha + receita | **Ver acompanhamentos sugeridos** — `cats=vinhos,azeites&mesa=sardinha` — ids de azeite (`MLB41319790`, `MLB20715667`, `MLB19885039` na jornada do navegador; outros azeites do Hub na API quando o catálogo virou) |
| Sugestões de acompanhamento para a receita de sardinhas com homus | a mesma | o mesmo tipo de CTA, sem exigir «marketplace» |
| Qual vinho combina com a receita de sardinhas com homus? | a mesma | CTA de azeites; vinhos da fonte sem SKU compatível |
| Agora sem álcool. (seguimento) | — | só azeites; ids novos; não reutiliza o CTA anterior |
| Qual vinho combina com peixe grelhado? | Wine Folly peixe (não sardinha) | Vinho Verde `MLB45873188` — estilo, sem nota de guia |
| Mesa de frios, pães e acompanhamentos | Wine Folly charcuterie | queijos, frios e azeites; **sem vinho** (o cliente não pediu) |
| Churrasco de porco e linguiça. Qual vinho? | Evino churrasco | orientação mantida; Hub sem Lambrusco/Cabernet Franc com atributo |
| Como acompanho o pagamento do meu pedido? | nenhuma | sem CTA culinário |
| O Sacramentos Sabina Entre Serras 2025 tem avaliação? | Descorchados 95/100, Informe Brasil 2026 | sem CTA comercial |

## Testes isolados × prova real

Isolados (`tests/test_prompt85.py` + 84/84A/82/81, 68 passed): catálogo controlado com Cava, Lambrusco e azeite. CTA sem o modelo chamar a ferramenta; seguimento sem álcool; estilo sem nota; alternativas sem transferir pontuação; sem correspondência ≠ Hub fora; persistência no painel; mesas anteriores.

Produção: Hub real, sem compra. Jornada no navegador (1440 e 390): pergunta → resposta → botão visível no fim da mensagem, acima do formulário → clique → vitrine «Para acompanhar as sardinhas» com os três azeites. Frios: clique → «Para sua mesa de frios». Reabrir o painel conserva fonte e CTA da última mensagem.

## Capturas

| Arquivo | O quê |
|---|---|
| `prod/chat-sardinhas-1440.png` / `390.png` | fonte + receita + **Ver acompanhamentos sugeridos** visível |
| `prod/vitrine-sardinhas-1440.png` / `390.png` | «Para acompanhar as sardinhas»; só azeites compatíveis |
| `prod/chat-frios-1440.png` / `390.png` | mesa de frios; CTA sugerido |
| `prod/vitrine-frios-1440.png` / `390.png` | queijos, presunto e azeites |
| `prod/chat-reopen-1440.png` | conversa reaberta com o mesmo CTA |
| `prod/chat-*.json` / `summary.json` | API ao vivo |
| `prod/catalog.json` | snapshot do Hub visto pela Loja |

## O que não mudou

Receitas, avaliações de guia, catálogo comissionado do Hub, pedidos, pagamentos, fidelidade, endereços, calendário, modelo AWS e credenciais. Sem produto fictício e sem alargar hints de vinho para fabricar correspondência.

## Rollback (sem restaurar banco antigo)

1. Voltar a imagem `lojadepaes:prod-20261007j` (ou `i` se for preciso o 84A puro).
2. Só a camada comercial do Gigio: `LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=false` e recreate da API. Chat, fontes e vitrine genérica permanecem.
