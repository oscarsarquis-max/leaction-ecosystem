# Prompt 75 — Publicação isolada de «Para acompanhar seu pão»

06/10/2026. Sem senhas. Sem pedido, e-mail, cobrança ou compra externa de teste.

## O que está publicado

| Peça | Estado |
|---|---|
| Código Loja | `lojadepaes:prod-20261006j` (não é a `h`) |
| Bundle | `/assets/index-DilXU1VT.js` |
| URL | https://lojadepaes.com.br/ e https://lojadepaes.com.br/acompanhar |
| Alembic | `a7d3b8e02c41` → `b8e4c1d93f50` (tabela `accompaniment_items`, aditiva) |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261006T193908Z.sql.gz` (75 333 bytes) |
| Hub marketplace | `https://actionhub.com.br/marketplace-api` — plugin Flask + proxy Next |
| Hub FE build | `70XS4IOjG8YxGNHbm3l8H` (rollback em `/var/lib/leaction-platform/rollback-prompt75-20261006T193130Z`) |
| Hub git_sha do health | `49b2a83` (env da caixa; não muda com publicação cirúrgica) |

## Flags efetivas

| Flag | Valor |
|---|---|
| `LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED` | **true** |
| `LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED` | **false** |
| `LOJADEPAES_ACCOMPANIMENTS_PREVIEW` | **false** |
| Gigio existente | **true** (Bedrock / Claude, atendimento comum intacto) |
| Pedidos / pagamentos / fidelidade | **true** |

Primeira carga fria após restart do API pode devolver `source_status=unavailable` (timeout 2 s do Hub). A chamada seguinte / cache quente serviu o perfil. `/operations` não consulta o Hub; `accompaniments_visible` fica true depois da primeira carga bem-sucedida.

## Separação pedida

| Afirmação | Evidência |
|---|---|
| Código publicado | imagem `j` no ar; rollback de app: `prod-20261006g` |
| Vitrine ativa | `GET /api/v1/accompaniments` → `enabled=true`, `source=hub`, `preview=false`, 32 itens |
| Catálogo real | permalinks `https://www.mercadolivre.com.br/p/MLB…`, fotos `https://http2.mlstatic.com/…`, CTA «Ver no Mercado Livre» |
| Fixture local | **não** publicada (nenhum «Azeite extra virgem (demonstração local)») |
| Gigio integrado aos complementos | **não** — flag própria desligada |
| Associação no pão | **pendente** — overlay `accompaniment_items` vazia; `/for-product/{slug}` sem itens |

## Registros editoriais do Hub (aditivos)

Inseridos/ampliados só estes IDs em `marketplace_curation`. TI (`formacao`, `equipamentos`, `software`) não foi alterado. `livros` não entrou.

- `vinhos`
- `queijos`
- `frios`
- `azeites`

Vitrine sem header continua legado de TI. Header `X-ActionHub-App-Id: lojadepaes` ou `?origin=lojadepaes` devolve as quatro prateleiras culinárias. Origem desconhecida: 400 + vazio.

Gateway, pagamentos e tema do Hub não foram republicados. Rollback Hub: restaurar `$RB/backend` e `$RB/next-build`, `pm2 restart marketplace-api action-hub`.

## Itens reais visíveis (amostra da carga quente)

Vinhos brancos (Amo.te, Mateus, Tricana, Arinto), gorgonzolas (Igor, Bergader, Cruzília), presunto Parma Sadia/Paesano, azeites portugueses (Serra Morena, Serrata, Fátima, Colavita, Monsaraz, Quinta da Alorna).

A busca ao vivo do ML ainda pode misturar ruído (ex.: «copa» → bola/chaveiro). Não é fixture e não é seleção SKU a SKU do proprietário. Ajuste fino de curadoria fica no painel do Hub.

## Preservado

`/operations`: pedidos, pagamentos e fidelidade ligados. Gigio comum pronto. Sem reset de banco, sem seed comercial, sem cópia do Postgres local.

## O que não foi feito

- Capturas desktop/390/320 no browser (ferramenta de browser ausente nesta sessão). Prova por HTML 200 + bundle + JSON da página/API.
- Overlay narrativa/pães no admin — o proprietário associa no painel `/admin/produtos/complementos` quando quiser.
- Consulta de complementos do Gigio — deixada desligada de propósito.

## Rollback

- Loja app: `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261006g` e `compose up -d api`. A tabela `accompaniment_items` pode permanecer.
- Desligar só a novidade: as duas flags de complemento em `false`.
- Hub: pasta `rollback-prompt75-20261006T193130Z`.
