# Prompt 88 — Instrução interna do Gigio

08/10/2026. Correção depois do Prompt 87 (`prod-20261007o`). Sem migração. Sem pedido real.

## Produção

| Peça | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261008a` (rollback: `prod-20261007o`) |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261008T085505Z.sql.gz` |
| Regras | `88` |

## Causa

O modelo escrevia `<invoke name="lookup_products">` como texto. A API só executava `tool_use` estruturado e devolvia o XML como resposta ao cliente.

## Correção

Texto de invocação não é executado. Resposta inválida tenta uma síntese; se falhar, mensagem honesta com tentar novamente. Consulta vazia de vitrine não lista o catálogo.

## Rollback

`LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007o` e recreate da API.
