# Parecer técnico — prova visual da revisão da nota (delta)

## O que estava errado

As capturas anteriores `nota-*` fotografaram `/entrar`. Causa: o script usava preview/OIDC (e, nesta correção, ainda podia cair no preview antigo `:5288` via `PANNE_EVIDENCE_PORT`) e o mock `**/api/**` interceptava módulos Vite `/src/api/*.ts`. Isso **não** prova a interface implementada.

## O que foi capturado agora

Sessão local **Vite DEV** `http://127.0.0.1:5291`, provedor falso de desenvolvimento (`panne.fakeSession=1`), **sem Demo**, **sem OIDC**, **sem nota 415395**.

| Arquivo | Estado | Viewport | URL final | `/entrar` |
|---|---|---|---|---|
| `nota-before__desktop-1440.png` | Antes de gravar | 1440 | `/gestao/compras/entradas/c0c0c0c0-c0c0-4c0c-8c0c-c0c0c0c0c0c0` | não |
| `nota-pending__desktop-1440.png` | Após **Gravar nota revisada**, mesma página | 1440 | a mesma | não |
| `nota-pending__celular-390.png` | Estoque pendente | 390 | a mesma | não |

Perfil: **Ana Padeiro** (desenvolvimento). Organização de ensaio: **Padaria Central** (`11111111-1111-1111-1111-111111111111`). Documento de ensaio: nota **104532**. Detalhe em `manifesto.json`.

Na captura desktop pendente: o clique em **Gravar nota revisada** manteve a rota; o lede passou a “Nota gravada · estoque pendente”; **Entrada no estoque** ficou na mesma página; **Confirmar entrada no estoque** habilitou.

## Comparação com `nota-salvar-separado-estoque.html`

| Peça | Cortex | Aplicação (1440) |
|---|---|---|
| Folha | `.page` 940 px | `.receipt-page` 1000 px (`62.5rem`) |
| Metadados | borda bloco 1 px | `.receipt-meta` borda topo/base 1 px |
| Revisão + duas ações + resumo | mesma folha | mesma folha (`.receipt-sheet`) |
| Ação 1 | Gravar nota revisada, largura da folha | botão 947 px |
| Ação 2 | Entrada no estoque, abaixo, desabilitada até gravar | mesma ordem; desabilitada antes, habilitada depois |

Diferença de largura: a app é **60 px mais larga** que o desenho (1000 vs 940). Título da app não ocupa a folha inteira (455 px). Em 390 px a leitura empilha; as duas seções e os dois botões permanecem visíveis.

## Ensaio API/banco descartável (contagens)

`test_save_review_does_not_touch_stock_then_receive_is_separate` — **1 passed** (4,29 s), Postgres local `127.0.0.1`, base lógica `panne`, organização criada no próprio teste. **Não** é produção. **Não** usou a nota 415395.

Depois de `POST .../review`: ingredientes, itens, locais, políticas, recibos, movimentos, saldos e histórico de custo **iguais** ao antes. Só `POST .../receive` cria esses efeitos.

## Testes já concluídos (não repetidos)

- `test_fiscal_review_without_stock` + `test_fiscal_receipt_http` + `test_fiscal_inbound`: **17 passed**
- `fiscal-028d.test.tsx` + `receiptReview.test.ts`: **15 passed**
- `tsc --noEmit`: ok

Erro, sucesso do lançamento, idempotência e isolamento ficam nesses testes. Sem captura nova desses estados.

## Fora desta passagem

Não houve publish, migrate nem seed em produção. A nota 415395, dados de cliente, Demo e demais rotas não foram alterados.
