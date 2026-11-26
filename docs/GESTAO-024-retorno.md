# GESTAO-024 — retorno

Branch: `feat/gestao-024-rendimento` (base `feat/gestao-023-entrada` / `b0059268`).
Imagem: `lojadepaes-gestao:024-20261123`. Sem merge na `main`. `GESTAO_SEM_BANCO=1`.

## Checklist

| # | Item | Feito | Evidência |
|---|------|-------|-----------|
| 1 | `git apply --check` limpo; 25 vitest + backend novos | sim | Patch Claude aplicado. Vitest: 25/25 (`rendimento025`, `receitas015/017/018`, `situacao019`). Backend: `tests/test_rendimento_024.py` + ajustes `test_perdas_013` (19 verdes no pacote de rendimento/perdas). |
| 2 | Item 3 — padrões Boulangerie | sim | Ver seção abaixo. |
| 3 | Capturas locais N=1 e N=8 | sim | `lojadepaes-gestao/docs/evidence/gestao-024-local/rendimento-n{1,8}-1280.png` + `capturas.md`. |
| 4 | Imagem no ar; loja 200; SSH fechado; commit+push sem merge | sim | `gestao-api` healthy `024-20261123`; gestao/health/ready/loja = 200; porta 22 fechada após o ciclo. |

## Item 3 — Boulangerie (prod)

Org: `849dfd4a-1613-4474-8b3a-586f95e794ab`.

**Já existiam (só leitura):** padrão específico de processo 5 % na faixa Forma 400–600 g (e demais específicos já cadastrados).

**Criados (autorizado Oscar 23/11):**
- processo 5 %, qualquer formato — obs. “padrão da casa, definido pelo Oscar em 23/11”;
- cocção 14 %, qualquer formato — mesma obs.

**Por que o Levain “pegava” e o Pão Rústico não:** o Levain resolvia processo com padrão/faixa que batia; o Rústico (600 g final → cru ~698 g) caía no buraco da tabela Forma (400–600 / 800–1000), a segunda busca apagava a cocção achada pelo peso final, e o publicar arredondava para 0 pão.

## Ordem de resolução (código)

manual → medido → padrão específico → referência do formato → **padrão geral da casa (5 % / 14 %)** → referência geral. Baguete segue 18 % da referência do formato.

## Observação SEM_BANCO

O YAML Forma unificado `[400, 1000]` vai na imagem; com `GESTAO_SEM_BANCO=1` o catálogo em prod não foi recarregado. Em produção o buraco é coberto por: (1) busca única pelo cru + faixa mais próxima com `confianca: baixa`; (2) padrões gerais 5/14 da Boulangerie.
