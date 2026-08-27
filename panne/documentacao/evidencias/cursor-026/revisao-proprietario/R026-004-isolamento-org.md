# Evidência R026-004 — terceira passagem (isolamento org + resíduos)

Data: 2026-08-27
Produto: Panne Demo
Sem commit / push / CURSOR-027.
Estado: **validada integralmente pelo Cortex** (esta passagem e o conjunto R026-004).

## Validação Cortex anterior (parcial nesta passagem)

### Aprovado

- Rastreabilidade sem erro de cancelamento.
- Eventos e quantidades humanizados.
- Plano com produto, código e unidade.
- Estoque agrega por unidade (sem seis casas).
- Lista de dossiês (receita, código público, versão, estado, próxima ação).
- Console limpo após reinício.

### Reprovado — vazamento visual entre organizações

Troca de org no cabeçalho mantinha dossiê da org A na mesma URL. Causa: `useAsyncResource` / loads com deps `[api, id]` sem `active?.organization_id`; identidade do `ApiClient` estável em `selectOrganization`.

## Correções desta passagem

### Isolamento

- `useAsyncResource`: troca de deps → `carregando` imediato; limpa dados/erro; geração; `enabled=false` limpa.
- Páginas escopadas passam a depender de `active?.organization_id` (ou chave equivalente) e limpam estado local na troca.
- Dossiê: limpa comparação/mentor/erros; comandos desabilitados durante carga; link humano para a lista em 404/403.

### Linguagem / quantidade / plural

- Catálogo `nutrient_*`, `may_contain`, `mandatory_*` completo.
- Conteúdo líquido `50.000000` → `50 g` (perfil + obrigatórias `conteudo_liquido`).
- Estoque: `6 posições` / `1 posição` via `pluralize`.

## Testes

```text
frontend: 140 passed (23 files)
inclui org-isolation.test.tsx (A→B→A, corrida, custos, relatórios, qty, plural)
```

## Reinício limpo

`stop-demo.ps1` + `start-demo.ps1` + health/ready antes da nova validação Cortex.
