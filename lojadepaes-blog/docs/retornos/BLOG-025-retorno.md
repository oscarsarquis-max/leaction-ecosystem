# BLOG-025 — retorno (lojadepaes-blog)

## Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Testes contrato | **Feito.** `tests/test_blog025_contrato.py` → 3 passed |
| 2 | `POST /api/receitas` | **Feito.** 201 `{ok:true,cliente_loja:false}`; depende de `python-multipart` |
| 3–4 | Enquete detalhe / produto pós-voto / histórico | Contrato mapeado; evidências em `claude/.../evidencias/BLOG-025/` |
| 5 | Deploy sem queda | Imagem `lojadepaes-blog:blog025-20261126b`; Loja/Gestão 200; lepain 502 só durante swap (~4s) |
| 6 | Este retorno | Na branch `feat/blog-025` |

## Escopo tocado

- `app/cms.py` — campos receita + `by_lang(..., "receita")`
- `app/rn.py` — `detalhe`, `produto` só com `votou`
- `app/receitas_api.py` + rota `POST /api/receitas` em `main.py`
- `requirements.txt` — `python-multipart`

Páginas públicas / templates: **não** alterados (BLOG-026).
