# GESTAO-026 — retorno

Branch: `feat/gestao-026-busca-item` (base `feat/gestao-025-excluir` / `c68c99e7`; main ainda sem o 025).
Imagem: `lojadepaes-gestao:026-20261123`. Sem merge na `main`. `GESTAO_SEM_BANCO=1`.

## Checklist

| # | Item | Feito | Evidência |
|---|------|-------|-----------|
| 1 | Testes novos + busca existentes | sim | `test_busca_item_026.py` + `test_ingrediente_busca.py`: **50 passed** |
| 2 | Captura local “nuvola” na receita | sim | `docs/evidence/gestao-026-local/busca-nuvola-receita-1280.png` |
| 3 | Auditoria Boulangerie (só leitura) | sim | `docs/GESTAO-026-auditoria.md` — 2 pares; nada juntado/excluído |
| 4 | Imagem no ar; loja 200; SSH fechado; push | sim | Tag `026-20261123` |

## Correção

Uma função `nomes_do_ingrediente` (nome, apelidos, itens, item+marca) alimenta `buscar`, `ingredientes_parecidos`, `pares_parecidos` e `sugerir`. Acerto por nome/apelido empata à frente do item; catálogo não sugere o que a padaria já tem pelo item.
