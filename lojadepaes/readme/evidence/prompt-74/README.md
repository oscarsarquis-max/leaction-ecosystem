# Prompt 74 — prévia local avaliável

Ambiente local, sem deploy. Flags de produção permanecem desligadas no exemplo de produção.

## URLs

| Superfície | Endereço |
|---|---|
| Loja | http://127.0.0.1:5175/ |
| Para acompanhar | http://127.0.0.1:5175/acompanhar |
| Admin (login no cabeçalho, modo local sem senha de produção) | http://127.0.0.1:5175/admin/produtos/complementos |
| API | http://127.0.0.1:5075/api/v1/health |

## O que é real vs demonstração

| Dado | Origem |
|---|---|
| Pães da vitrine (9) e receita em destaque | Catálogo editorial **público** de produção, importado em leitura |
| Pão teste Prompt 16 | Já existia no banco local; preservado |
| Complemento, preço e link comercial | **Fixture local** — Hub `:4012` não estava no ar |
| Gigio | Modo de desenvolvimento (`fake`), identificado na prévia |
| Pedidos, e-mail, pagamento | Sem efeito real nesta prévia (`MAIL_IDENTITY_READY=false`) |

A fixture **não** comprova integração comercial. Sem destino validado do Hub o botão de compra fica desligado.

## Flags só na prévia local

`PUBLIC_ACCOMPANIMENTS_ENABLED`, `GIGIO_ACCOMPANIMENTS_ENABLED` e `ACCOMPANIMENTS_PREVIEW` em `true` no `.env` local. Em `production` a prévia não liga mesmo com a flag.

Menu “Para acompanhar” não depende de cache quente: com prévia local a entrada aparece na primeira carga, sem chamar o Hub em `/operations`.

## Isolamento

Backup antes do import: `var/backups/lojadepaes-local-20261006T150439Z.sql` (gitignored). Sem reset. Sem cópia de pedidos, CPF, tokens ou outbox.
