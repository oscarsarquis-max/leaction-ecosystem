# BLOG-025 — retorno (Loja de Pães)

## Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Testes | **Feito.** `tests/test_integracoes_lepain_025.py` → 4 passed |
| 2 | Rotas integracao | `GET .../fidelidade/cliente`, `POST .../fidelidade/credito` (idempotente `lepain-*`), `GET .../vitrine` |
| 3 | Proteção | `X-Service-Key`, rate limit, log sem telefone |
| 4 | Deploy | Imagem `lojadepaes:prod-blog025-20261126b`; Loja/Gestão/lepain 200; migração `a8c1d9e24f70` (índice único só `lepain-%`) |
| 5 | Crédito prod | **Pendente** — aguarda telefone de cliente de teste do Oscar |
| 6 | Este retorno | Branch `feat/blog-025-loja` |

## Escopo

Só as rotas da seção 3 do prompt (+ leitura de vitrine). Demais da Loja intocado.
