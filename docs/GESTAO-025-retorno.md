# GESTAO-025 — retorno

Branch: `feat/gestao-025-excluir` (rebase em `main` / `551ef6e3`).
Imagem: `lojadepaes-gestao:025-20261123`. Sem merge na `main`. `GESTAO_SEM_BANCO=1`.

## Checklist

| # | Item | Feito | Evidência |
|---|------|-------|-----------|
| 1 | `git apply --check` limpo; 37 vitest + backend novos | sim | Patch Claude aplicado. Vitest 37/37 (`ingrediente025` + `fluxo`). Pytest `test_excluir_025.py`: 6 verdes. |
| 2 | Capturas locais Excluir + confirmação | sim | `lojadepaes-gestao/docs/evidence/gestao-025-local/` |
| 3 | Imagem no ar; loja 200; SSH fechado; commit+push sem merge | sim | Tag `025-20261123`; porta 22 fechada após o ciclo. |

## O que entrou

- Front: botão **Excluir** só sem saldo/item/lote/movimento; confirmação; 409 mantém o modal com o motivo.
- Back: `DELETE /ingredientes/{id}` (`lancar`); 204 se limpo; 409 `em_uso` com motivo em português.
