# Precificação e calculadora

**Ciclo:** CURSOR-028-A.  
**Base existente:** CURSOR-012/021 — `costing_pricing`, `VOCABULARIO-CUSTOS-E-PRECOS.md`, `ADR-CUSTOS-E-PRECOS.md`.  
**Fórmulas já no código:** `markup_factor`, `markup_percent`, `gross_margin`, `contribution_margin` em `costing_pricing/formulas.py`.

## Objetivos 028

Tornar preços **explicáveis e auditáveis** no fluxo Produto–Receita–Combo, com histórico e calculadora contextual — sem misturar na ficha de cozinha.

---

## 1. Históricos

| Histórico | Chave | Evento | Uso |
|---|---|---|---|
| Preço de compra | ingrediente + fornecedor (+ opcional establishment) | vigência manual **e** linha de recebimento/NF | custo de reposição e auditoria |
| Custo de receita | formulation_version (+ ordem) | snapshot previsto; custo real pós-execução | planejado×realizado |
| Preço de produto | product_id | publicação de preço / vigência | PDV e margem |
| Preço de combo | product_combo_id | preço **próprio** | não forçar soma dos componentes |

Lacuna atual: UI/API unificada “histórico por NF” além de `IngredientPrice` vigente — cobrir em **028-D** e **028-H**.

---

## Precedência de markup

```
produto (regra própria)
    ↓ se ausente
família (entidade organizacional)
    ↓ se ausente
organização
```

- Toda aplicação registra **qual nível venceu** na memória de cálculo.
- Família: entidade organizacional (decisão 028-B).
- Combo: markup/preço próprio; custo derivado dos componentes para margem.

---

## 3. Markup × margem (matemática)

Sejam \(C\) custo e \(P\) preço.

| Conceito | Definição | Relação |
|---|---|---|
| Markup sobre custo | \(P = C \times (1 + m)\) ou \(P = C \times k\) (fator) | \(m = (P-C)/C\) |
| Margem sobre venda | \(g = (P-C)/P\) | \(g = m/(1+m)\) (se \(m\) sobre custo) |

- Nunca tratar markup e margem como sinônimos na UI.
- Vocabulário alinhado a 021; labels explícitos (“markup sobre custo”, “margem bruta sobre preço”).

---

## 4. Vigência e auditoria

Toda regra de preço/markup/custo publicado:

- `valid_from` / `valid_to`
- autor, motivo, documento de origem (opcional)
- imutabilidade do passado (nova vigência = novo registro)
- memória de cálculo serializada (inputs, fatores, arredondamentos, nível de precedência)

---

## 5. Calculadora lateral contextual

| Contexto da tela | Painel mostra |
|---|---|
| Ingrediente | último preço compra, fornecedor, tendência curta |
| Receita / versão | custo previsto da batelada / kg / unidade |
| Ordem | previsto vs realizado parcial |
| Produto | custo → markup vigente → preço; margem |
| Combo | custo componentes + preço próprio + margem |

Regras UX:

- Só com permissão costing/pricing.
- Não aparece em execução de cozinha.
- “Por que este preço?” → expande memória (nível de regra, C, m, arredondamento).
- Planejado vs realizado lado a lado quando houver ordem.

Backend: reutilizar engines 021; 028-H é sobretudo contrato UX + precedência família + combo.

---

## 6. Arredondamentos, unidades e escalas

| Tema | Regra proposta |
|---|---|
| Moeda | arredondamento configurável por org (ex.: 2 casas; half-up) — documentar na memória |
| Quantidades | respeitar escala da unidade (g, kg, un); converter só via tabela de unidades |
| Preço unitário | calcular na unidade de venda do produto |
| Custo batelada / kg / un | três projeções da **mesma** memória (como 012) |
| Comparações | nunca misturar unidades sem conversão explícita |

---

## 7. Critérios de aceite (028-H)

1. Alterar markup só na família atualiza produtos sem regra própria; produtos com regra própria inalterados.
2. Memória de cálculo lista nível vencedor e fórmula.
3. Kitchen print / UI execução sem qualquer campo monetário.
4. Combo: preço próprio ≠ soma automática obrigatória; margem usa custo derivado.
5. Histórico de compra consulta preço por período e por fornecedor.
