# ADR — Conformidade e rotulagem (CURSOR-020)

Data: 2026-08-23. Jurisdição: Brasil.

## Decisão

O primeiro recorte produtivo de Conformidade e Rotulagem reutiliza o motor fechado de `compliance`, a projeção nutricional técnica existente e a biblioteca de conhecimento. A saída é sempre uma **proposta técnica para revisão humana**. Não existe selo, certificado ou expressão “Conforme Anvisa”.

## Reconciliação

| Módulo existente | Reúso | Não duplicar |
|---|---|---|
| `compliance.engine` | operadores fechados e estados mapeados | segundo motor |
| `nutrition_calculation` / `calculation_engine.nutrition` | snapshot técnico bruto | arredondamento no cálculo técnico |
| `knowledge_grounding` | fontes versionadas e orientação vs norma | crawler ou fonte executável |
| `formula_lab` | snapshot da formulação e produto técnico | segundo cadastro de receita |
| `ai_orchestration` | só explicação futura, com selo | IA que avalia, publica ou aprova |

Estados do motor (`insufficient_data`, `manual_review`) são mapeados na camada de rotulagem para `insufficient_evidence` e `manual_review_required`. O vocabulário do motor não muda.

## Consequências

- Declaração regulatória é projeção versionada, não reescrita do cálculo técnico.
- Aplicabilidade nunca é inferida pelo nome do produto ou da organização.
- Atualização normativa não altera avaliação antiga.
