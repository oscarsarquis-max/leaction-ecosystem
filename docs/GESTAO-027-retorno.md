# GESTAO-027 — retorno

**Branch:** `feat/gestao-027-parecidos` (`fcdce18e`, base `ddc80182`)  
**Imagem:** `lojadepaes-gestao:027-20261123`  
**Deploy:** `GESTAO_SEM_BANCO=1` (sem migração)

## O que mudou

- Busca continua solta (marca/item, como no 026).
- Duplicidade estrita: tira marca e palavras genéricas (`PALAVRAS_GENERICAS_DUPLICIDADE`) antes de comparar; o que sobra decide.
- `pares_parecidos[].motivo` em uma frase; tela com **Revisar** / **Não são o mesmo**.
- Par em `marcarDistintos` some da lista e não bloqueia edição.

## Checklist

| # | Item | Feito | Evidência |
|---|------|-------|-----------|
| 1 | `git apply --check` limpo + 37 vitest + backend novos | sim | patch Claude; vitest 37; `test_parecidos_027.py` 5 passed |
| 2 | Pares Boulangerie com regra nova (só leitura) | sim | `docs/GESTAO-027-auditoria.md` — **0** pares |
| 3 | Imagem no ar, loja 200, SSH fechado, commit+push sem merge main | sim | imagem `027-20261123`; ver commit desta branch |
