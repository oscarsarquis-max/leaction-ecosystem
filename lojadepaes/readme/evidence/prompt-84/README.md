# Prompt 84 — Mesa de frios e pratos do mar

07/10/2026. Autorização do proprietário nesta tarefa: ampliar e publicar o piloto. Sem degustação, revisão pessoal, parceria, sommelier ou «Escolha de A Loja». Revisão técnica: `agente-revisao-assistida`.

## Produção efetiva

| Peça | Valor |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007g` (rollback de app: `prod-20261007f`; não usar `h`) |
| Bundle | `/assets/index-B1tJLCHz.js` (sem redesenho) |
| Alembic | `e2b8f4a07d91` (aditivo: `frios` no check de categoria) |
| Flag especializada | `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true` |
| Flags preservadas | Gigio comum on; vitrine pública on; complementos on |
| Regras | `84` |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Backup no host: `/opt/lojadepaes/backups/lojadepaes-20261007T194255Z.sql.gz`. Sem cópia do banco local e sem seed comercial global.

## Cobertura por tema

| Tema | Estado em produção | Fonte | Afirmação permitida |
|---|---|---|---|
| Churrasco de porco/linguiça | publicada (83) | Evino, 18/01/2026 | Lambrusco ou Cabernet Franc só no churrasco |
| Tábua de queijos | publicada (83) | Evino, 05/02/2026 | Brancos / brut / Chardonnay como curinga da tábua — não da mesa de frios inteira |
| Mesa de frios | publicada | Wine Folly, Nicole Dickerson (WSET) | Variar queijos e embutidos; pão como base; fruta/castanha/azeitona/pasta como apoio; bebida opcional |
| Peixe grelhado | publicada | Wine Folly, Madeline Puckette | Tipo e preparo mudam a escolha; magro em lascas → Vinho Verde / Verdejo / Sauvignon Blanc / Albariño; não é «todo peixe pede branco» |
| Sardinhas | publicada | mesma guia Wine Folly, grupo de sabor intenso | Espumante/rosé seco ou tinto de tanino baixo; a receita da Loja **não** prova a bebida |
| Camarão leve (cítrico/ervas) | publicada | Wine Folly, Albariño | Albariño/Alvarinho nesse preparo; não cobre lagosta nem molho de tomate picante |
| Lagosta por preparo | publicada | Decanter, Chris Mercer, 12/04/2022 | Vapor/leve → mineral/Chablis; grelha/manteiga/thermidor → Chardonnay mais rico; Champagne; evitar tinto tânico; não é camarão |
| Outros crustáceos como classe | lacuna | — | Sem registro; caranguejo na página do Albariño não vira classe |
| Camarão com molho picante de tomate | lacuna | — | Orientação geral do Gigio, sem fonte especializada |
| Quantidades/conservação | não publicada | — | Sem valores universais nem tempo fora da geladeira |

Rascunhos 82 (`wine-dao-leitao`, método Evino, Canastra IG, Embrapa) continuam fora da recuperação.

## Prova isolada

`tests/test_prompt84.py` + regressão 80/81/82/77: **64 passed**. Cobre mesa sem vinho, sem carne+sem álcool, só queijos, natureza errada, Hub down, pergunta de pedido, churrasco/tábua sem vazamento, receita de sardinhas, escopo peixe/camarão/lagosta, seguimento camarão sem álcool.

## Prova em produção (API servida, Bedrock)

Conversas genéricas, sem dados de cliente. JSON em `prod/`.

| Pergunta | Fonte | CTA / ofertas |
|---|---|---|
| Mesa de frios, pães e acompanhamentos | só Wine Folly charcuterie | `/acompanhar?cats=frios,queijos,azeites&mesa=frios` — gorgonzolas, salames e azeites do Hub; **sem vinho** |
| Sem carne e sem álcool | — | `cats=queijos,azeites&mesa=frios` — queijos e azeites; sem embutido e sem vinho nos ids |
| Receita de sardinhas com homus | Wine Folly peixe intenso + link da receita real | azeites; título da vitrine «Para acompanhar as sardinhas» |
| Peixe grelhado | Wine Folly (título de peixe, não de sardinha) | Vinho Verde `MLB45873188` (estilo citado) |
| Camarão com limão e ervas | Wine Folly Albariño | sem CTA: Hub sem Albariño/Alvarinho verificável |
| Lagosta grelhada com manteiga | Decanter | sem CTA: Hub sem Chablis/Chardonnay/Champagne verificável |
| Seguimento sardinha → camarão sem álcool | nenhuma fonte de vinho | só azeites, `mesa=camarao` |
| Churrasco de porco | só Evino churrasco | orientação mantida; Hub atual sem Lambrusco/Cabernet Franc com atributo |
| Tábua de queijos | só Evino queijos | vinhos+queijos do Hub |
| Pagamento do pedido | nenhuma | sem CTA comercial |

Receita publicada confirmada: `Sardinhas e Homus de Grão-de-Bico Fresco (Tartine Bread)` → `/receitas/sardinhas-e-homus-de-grao-de-bico-fresco-tartine-bread`.

A primeira chamada de complementos após recreate pode voltar sem CTA (timeout curto do Hub). A jornada seguinte, com o Hub quente, devolveu a vitrine.

## Navegador servido

A primeira tentativa headless estourou 180s porque o script clicava o primeiro `button.text-button` da home (não o Gigio) e o envio nunca partia. Isso era defeito do teste, não da API (~12s). O script passou a abrir só o painel, preencher o campo controlado e interceptar `POST /api/v1/gigio/chat`. Jornada real em 27s.

| Captura | O quê |
|---|---|
| `prod/gigio-open-1440.png` | painel aberto |
| `prod/chat-frios-1440.png` / `390.png` | mesa de frios; fonte Wine Folly visível; CTA no payload interceptado |
| `prod/chat-sardine-1440.png` / `390.png` | receita identificada; fonte de sardinha, não de queijo/churrasco |
| `prod/vitrine-frios-cta-1440.png` / `390.png` | «Para sua mesa de frios»; queijos, presunto e azeites; sem vinho; fotos `contain`; 3/1 colunas; aviso de comissão e data informada |
| `prod/vitrine-sardine-cta-1440.png` / `390.png` | «Para acompanhar as sardinhas»; só azeites |

Intercepto: `prod/intercepted-chat.json`. Sem e-mail, pedido, compra ou cobrança.

## Rollback (sem restaurar banco antigo)

1. Só os registros novos: arquivar `board-mesa-frios`, `wine-peixe-grelhado`, `wine-sardinhas`, `wine-camarao-leve`, `wine-lagosta`. Churrasco e tábua 83 permanecem.
2. Só a camada especializada: `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=false` e recreate da API.
3. App anterior: `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007f`.
4. Não restaurar dump sobre vendas.

SSH desta sessão: Lightsail liberou só `189.14.176.74/32` em `:22`. Sem porta aberta ao mundo.
