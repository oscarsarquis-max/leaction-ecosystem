# Espinha dorsal do fluxo produtivo

**Ciclo:** CURSOR-028-A (especificação) · decisões fechadas em 028-B.  
**Status:** canônico para implementação.  
**Escopo 028-B:** navegação `/fluxo` (sem Produto/Combo/sub-receita/estoque FG novos).

## Decisões do proprietário (vinculantes)

1. Produto não exige receita.
2. Receita é definição de transformação produtiva, não o cadastro do produto.
3. Produto pode ser: produzido; comprado; combo; abastecimento misto (quando justificável).
4. Combo pode misturar produtos comprados e produzidos.
5. Receita pode resultar em produto final, preparo intermediário ou componente de outra receita.
6. Receita final pode usar ingredientes e sub-receitas.
7. Ordem de produção normalmente nasce de produto produzido.
8. Ordem direta de receita permanece para intermediários, testes e produção para estoque.
9. Produto comprado não passa por ordem de produção.
10. Combo não é modelado artificialmente como receita.
11. Jornada imediatamente visível e sequencial.
12. Impressão operacional sem valores; gerencial com custos/indicadores.
13. Cálculos explicáveis e auditáveis.

## Decisões fechadas (028-B)

1. **Receita vigente** por organização + estabelecimento + vigência temporal.
2. **`TechnicalProduct` evolui para Produto** — sem entidade concorrente.
3. **Modalidade mista** exige decisão explícita por abastecimento (compra vs produção) a cada evento.
4. **Combo virtual por padrão** (reserva/baixa dos componentes; sem SKU de estoque do combo).
5. **Família** é entidade organizacional.
6. **Intermediário** é Produto (não Ingrediente duplicado).

## Princípio estruturante

```
Produto  = identidade comercial/operacional (o que se vende, estoca, rotula, precifica)
Receita  = transformação versionada (como se produz, quando houver produção)
Combo    = composição comercial de produtos (não é transformação)
Ordem    = execução de uma receita (ou de um produto produzido vinculado a receita vigente)
```

Estoque de ingredientes, compras e lotes alimentam produção e revenda.  
Produto acabado e combos precisam de identidade e rastreio próprios (hoje parcialmente ausentes).

## Fluxo canônico (visão única)

```
Compras/recebimento → Lotes/estoque de insumos
        ↓
Ingredientes / itens compráveis
        ↓
┌───────────────────┬────────────────────┬─────────────────┐
│ Produto comprado  │ Produto produzido  │ Produto combo   │
│ (sem receita)     │ (+ receita opcional│ (componentes)   │
│                   │   vigente)         │                 │
└─────────┬─────────┴─────────┬──────────┴────────┬────────┘
          │                   │                   │
          │         Plano → Ordem → Execução      │
          │                   │                   │
          └──────────→  Produto acabado / estoque FG  ←─────┘
                              ↓
                    Rotulagem · Custos · Preços · Relatórios
```

## Oito etapas da jornada (navegação)

| # | Etapa | Intenção | Reuso principal hoje |
|---|---|---|---|
| 1 | Compras e recebimentos | Abastecer insumos e mercadorias | `/gestao/compras/*` |
| 2 | Ingredientes e estoque | Cadastro, lotes, movimentações | `/componentes/*` |
| 3 | Produtos | Identidade comercial/operacional | **lacuna** (só `TechnicalProduct` via receita) |
| 4 | Receitas | Transformação versionada | `/receitas/*` |
| 5 | Planejamento e ordens | Demanda → ordem | `/planejamento`, `/ordens`, `/producao` |
| 6 | Preparo e execução | Chão de fábrica | `/producao/ordens/:id/executar` |
| 7 | Produto acabado e rotulagem | FG + conformidade | rotulagem sim; FG estoque **ausente** |
| 8 | Custos e preços | Formação e histórico | `/gestao/custos/*` |

Detalhe de navegação: `NAVEGACAO-FLUXO-PRODUTIVO.md`.  
Modelo de dados: `MODELO-PRODUTO-RECEITA-COMBO.md`.  
Lacunas: `MAPA-REUSO-E-LACUNAS-FLUXO.md`.

## Exemplos canônicos (aceitação)

| Exemplo | Produto | Receita | Ordem | Estoque |
|---|---|---|---|---|
| Bolo de chocolate | Vendável | Final + sub-receitas massa/cobertura | Sim | Insumos + FG bolo |
| Pão carioca | Vendável | Direta | Sim | Insumos + FG pão |
| Coxinha | Vendável | Massa + recheio + montagem | Sim (pode gerar intermediários) | Insumos + intermediários + FG |
| Suco engarrafado | Comprado | Não | Não | Lote mercadoria |
| Combo café da manhã | Combo | Não | Não (consome componentes) | Reserva/separação dos componentes |

## Perfis e custo

- Operador de cozinha / padeiro: vê fluxo 5–7 e fichas **sem** valores.
- Gestor / comercial / owner: vê custos, markup, margem e impressões gerenciais.
- Permissões existentes (`costing.*`, `pricing.*`, `reporting.costing/pricing`) continuam como gate.

## Documentos deste ciclo

| Arquivo | Conteúdo |
|---|---|
| `MODELO-PRODUTO-RECEITA-COMBO.md` | Modelo canônico |
| `MAPA-REUSO-E-LACUNAS-FLUXO.md` | Inventário e reuso |
| `NAVEGACAO-FLUXO-PRODUTIVO.md` | Página Fluxo + wireframes |
| `IMPRESSOES-OPERACIONAIS-E-GERENCIAIS.md` | Contratos de impressão |
| `PRECIFICACAO-E-CALCULADORA.md` | Preços e calculadora |
| `PLANO-CURSOR-028.md` | Entregas 028-B…I |
