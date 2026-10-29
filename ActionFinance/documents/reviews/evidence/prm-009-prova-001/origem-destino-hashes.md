# Comparação origem/destino — restrita (hashes)

Janela: 2026-10-02T13:48:24Z–13:48:25Z. Sem ids de encomenda, valores nominais, e-mails ou credenciais.

| Campo | Valor |
|---|---|
| Empresa | `624023a4-57e3-415c-b7d0-925ca1acd3b7` (Loja) |
| Ambiente | PRODUCTION |
| Origem declarada | ACTIONHUB_PAY via `api.actionhub.com.br` |
| Destino observado | Spider `resultSummary.reviews` + store do Monitor |
| list1 | `afm-prova001-20261002T134747Z` / `afp-prova001-20261002T134747Z` · READY · reviewCount=9 · itemCount=0 |
| list2 | `afm-prova001-20261002T134747Zb` / `afp-prova001-20261002T134747Zb` · READY · reviewCount=9 |
| Identidades | 9 hashes SHA-256[:12] iguais nas duas respostas |
| Prefixos (restrição) | `2ea5bcc511e1`, `2f9fdc29614f`, `3648cc5c84ed` |
| Pago | ausente nas 9 (review, não item automático) |
| Hub CloudWatch neste account | não existe grupo `/leaction` / `/actionhub` |
| Persistência AF desta prova | não escrita (sonda satélite). Títulos da Loja continuam 0; `txn_loja=9` |

A igualdade de hashes comprova a mesma janela de identidade no destino. Não substitui o ficheiro bruto da origem Hub, que não está neste account.
