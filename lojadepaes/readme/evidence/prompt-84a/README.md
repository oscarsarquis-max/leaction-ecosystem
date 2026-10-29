# Adendo 84A — ADEGA Brasil e Descorchados

07/10/2026. Incremento isolado depois do Prompt 84 (`prod-20261007g`). Sem degustação, parceria, sommelier, média entre guias ou «Escolha de A Loja». Revisão técnica: `agente-revisao-assistida`. Sem compra de assinatura e sem cópia de catálogo.

## Produção efetiva

| Peça | Valor |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007i` (rollback de app: `prod-20261007g`; não usar `h`) |
| Bundle | `/assets/index-DUyLrOkC.js` |
| Alembic | `f3c9a1b28e04` (aditivo: `guide_evaluation` e `evaluation`) |
| Flag especializada | `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true` |
| Flags preservadas | Gigio comum on; vitrine pública on; complementos on |
| Regras | `84a` |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Backup no host: `/opt/lojadepaes/backups/lojadepaes-20261007T201233Z.sql.gz`. Sem cópia do banco local e sem seed comercial global.

## Quatro camadas (não misturar)

| Camada | O que ficou | Disponível ao Gigio? |
|---|---|---|
| Fonte cadastrada para pesquisa | ADEGA Brasil Guia 2026 (página da loja da editora); Descorchados Informe Brasil 2026 (PDF oficial) | só como localizador, se a pergunta nomeia o guia |
| Avaliação verificada | duas fichas lidas no Informe Brasil 2026, escala 100 de Patricio Tapia | **sim** — só quando o rótulo é nomeado ou a oferta tem a mesma identidade |
| Conteúdo publicado | as duas avaliações + os dois localizadores + o piloto 83/84 intacto | sim, nos papéis certos |
| Oferta do Hub correspondente | nenhuma das duas identidades | não há anúncio que herde a nota |

### Avaliações que o Gigio de fato usa

Consultadas em 07/10/2026 no PDF oficial `https://www.guiadescorchados.cl/archivos/originales/9d93c9af2f50f9023e344c1a0184df84.pdf`.

| Produtor | Rótulo | Safra | Edição | Nota | Escala | Chave |
|---|---|---|---|---|---|---|
| Sacramentos Vinifer | Sabina Entre Serras Sauvignon Blanc | 2025 | Informe Brasil 2026 | 95 | 100 | `eval-descorchados-sacramentos-ses-sb-2025` |
| Casa Almeida Barreto | Paralelas Cabernet Franc | 2024 | Informe Brasil 2026 | 94 | 100 | `eval-descorchados-almeida-paralelas-cf-2024` |

A casa Almeida Barreto é Bodega del Año da edição; isso não transfere nota a outro Paralelas.

### O que não ficou disponível

| Item | Motivo |
|---|---|
| Qualquer nota ADEGA | a página comercial descreve a 15ª edição (2026); fichas individuais exigem o volume pago, não consultado |
| Outros vinhos listados no informe | quantidade não é meta; sem ficha lida para uso no chat |
| Ebook ADEGA em site de terceiro | acesso não autorizado; não usado |
| Recorte Zinio | insuficiente para prova |

Os guias **não** estão «integrados» só porque as URLs foram cadastradas. ADEGA permanece localizador com fichas pendentes.

## Correspondência com oferta

A nota só acompanha anúncio com produtor + linha/variedade + safra. Outra safra, outra linha, anúncio sem ano ou título genérico não herda. Estilo (Sauvignon Blanc, Cabernet Franc) não transfere pontuação. Harmonização continua só nas referências `pairing` do 83/84.

No Hub atual não há oferta com essas identidades. O CTA comercial, quando aparece, é vitrine do marketplace — não certifica a nota.

## Prova isolada

`tests/test_prompt84a.py` + regressão 84/82/81/77: **68 passed**. Cobre publicação, pergunta de prato sem nota, rótulo nomeado, estilo sem herança, ADEGA só localizador, correspondência exata / safra / linha / anúncio genérico, piloto anterior intacto, flag desligada.

Frontend: avaliação com edição e safra em «Sobre esta sugestão».

## Prova em produção

JSON em `prod/`. Sem e-mail, pedido, compra ou cobrança.

| Pergunta | Fonte no chat | Papel | Nota herdada? |
|---|---|---|---|
| Sacramentos Sabina 2025 tem avaliação? | Descorchados, 95/100, safra 2025 | evaluation | só deste rótulo |
| Almeida Paralelas CF 2024 tem nota? | Descorchados, 94/100, safra 2024 | evaluation | só deste rótulo |
| Qual Sauvignon Blanc com peixe grelhado? | Wine Folly peixe | pairing | não |
| Qual vinho com peixe grelhado? | Wine Folly peixe | pairing | não |
| Vocês usam o ADEGA 2026? | página da editora, fichas pendentes | informational | não |
| O que é o Descorchados? | informe, sem ficha | informational | não |
| Mesa de frios | Wine Folly charcutaria | pairing | — |
| Churrasco de porco | Evino | pairing | — |
| Pagamento do pedido | nenhuma | — | — |

Navegador servido: `prod/chat-sacramentos-1440.png` / `390.png` (guia, edição, 95/100, safra; aviso de que não prova harmonização); `prod/chat-peixe-1440.png` (Wine Folly, sem nota).

## Rollback (sem restaurar banco antigo)

1. Só o incremento: arquivar `guide-adega-brasil-2026`, `guide-descorchados-informe-brasil-2026`, `eval-descorchados-sacramentos-ses-sb-2025`, `eval-descorchados-almeida-paralelas-cf-2024`. O piloto 83/84 permanece.
2. Só a camada especializada: `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=false` e recreate da API.
3. App anterior: `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007g`.
