# Mapa de reuso e lacunas — fluxo produtivo

**Ciclo:** CURSOR-028-A.  
**Método:** inspeção de módulos backend (Alembic até `0020`), rotas HTTP, testes e UI `frontend/src`.  
**Regra:** não inferir capacidade só pelo nome da tela.

Legenda de estado: **completo** | **parcial** | **ausente** | **ambíguo**.

---

## Inventário por conceito

| Conceito | Entidade atual | Tabela(s) | API | Rota UI | Permissões (típicas) | Estado | Reuso |
|---|---|---|---|---|---|---|---|
| Ingredientes | `Ingredient` | `ingredients` (+ allergens/nutrition) | `/ingredients` | `/componentes/ingredientes` | catalog / ingredients | completo | Alto |
| Unidades | `Unit` / conversões | units | `/units` | (embutido em formulários) | catalog | completo | Alto |
| Fornecedores | `Supplier` | suppliers | `/suppliers` | `/gestao/compras/fornecedores` | procurement | completo | Alto |
| Itens de fornecedor | `SupplierItem` | supplier_items | sob suppliers / items | detalhe fornecedor | procurement | completo | Alto |
| Preços de compra | `IngredientPrice` | ingredient_prices | prices em ingredients/suppliers | custos / ingredientes | costing / catalog | completo | Alto — base p/ histórico NF |
| Compras (PR→PO) | Purchase* | purchase_* | `/inventory/procurement/*` | `/gestao/compras/*` | procurement.* | completo | Alto |
| Recebimentos | `GoodsReceipt` + lines | goods_receipts* | receipts | `/gestao/compras/recebimentos` | procurement | completo | Alto — enriquecer vínculo NF/histórico |
| Devoluções | returns | returns | returns | compras | procurement | completo | Médio |
| Lotes | `InventoryLot` | inventory_lots | inventory lots | `/componentes/lotes` | inventory | completo | Alto |
| Estoque / moves | `InventoryItem`, moves, reserves, picks, counts | inventory_* | `/inventory/*` | `/componentes/estoque`, picks, contagens | inventory.* | completo | Alto p/ insumos; **não** FG |
| Produto técnico | `TechnicalProduct` | technical_products | efeito de `/recipes` | **sem CRUD produto** | formula | **parcial** | Médio — base p/ Product |
| Produto comercial | — | — | — | — | — | **ausente** | — |
| Modalidade abastecimento | — | — | — | — | — | **ausente** | — |
| Receitas / versões | `Formulation`, `FormulationVersion`, items, steps | formulations* | `/recipes`, versions | `/receitas`, `/receitas/:id` | formula.* | completo | Alto |
| Sub-receitas | role `preparation` → ingredient; `ProductionOrderDependency` | formulation_items; dependencies | parcial | UI limitada | formula / production | **ambíguo / parcial** | Baixo até reformular |
| Vínculo produto–receita vigente | implícito (produto criado com receita) | — | — | — | — | **ambíguo** | — |
| Planos | production plans | plans | `/production/plans` | `/planejamento` | production.plan | completo | Alto |
| Ordens | `ProductionOrder` | production_orders | `/production/orders` | `/ordens`, `/producao` | production.* | completo | Alto |
| Execução | steps, events, issues | execution* | execute / events | `/producao/ordens/:id/executar` | production.execute | completo | Alto |
| Ficha de produção | issue JSON + HTML print | — | sheet endpoints | impressão ordem/receita | production | **parcial** (HTML, não PDF) | Alto p/ contrato |
| Rendimento / perdas | yields, loss events | production yields/events | orders | execução + relatórios | production / reporting | completo | Alto |
| Produto acabado (estoque) | `good_units` na ordem | — | order complete | — | production | **ausente** (sem depósito FG) | — |
| Rotulagem | labeling modules | labeling* | labeling | conformidade / impressão | labeling.* | completo | Alto |
| Custos | snapshots, memory | costing* | `/costing/*` | `/gestao/custos` | costing.* | completo | Alto |
| Preços / markup | pricing rules, formulas | pricing* | `/pricing/*` | `/gestao/custos/precos` | pricing.* | completo | Alto — falta hierarquia família |
| Relatórios | reporting HTML/CSV | — | `/reporting/*` | `/relatorios` | reporting.* | completo | Alto |
| Impressões | `window.print` + `print.css` | — | HTML sheets | várias | por domínio | **parcial** | Separar cozinha vs gestão |
| Assistentes | recipe AI + global 024/025 | — | assistants | shell | conforme rota | completo | Médio — alinhar a “Fluxo” |
| Combo | — | — | — | — | — | **ausente** | — |
| Docs técnicos / biblioteca | stubs | — | — | — | — | ausente / stub | Ignorar no 028 |

---

## Navegação atual vs desejada

| Observação | Evidência |
|---|---|
| Shell: Produção, Componentes, Receitas, Conformidade, Gestão, Relatórios | `Shell.tsx` |
| Mobile ≤900px: menu hambúrguer | CSS shell |
| **Não existe** página persistente “Fluxo produtivo” | — |
| Quadro tem visão “Fluxo por estado” | cards de status de OP — **não** é a jornada 1–8 |
| Custos ocultos a produção/ops | permissões + UI gates |

---

## Reuso prioritário (028-B em diante)

1. **Manter e conectar:** procurement, inventory (insumos), recipes, plans/orders/execution, costing/pricing, labeling, reporting, prints HTML.
2. **Estender:** `TechnicalProduct` → Product com modalidade; recebimento → histórico de preço por NF; ficha → variantes cozinha/gestão.
3. **Criar:** página Fluxo; vínculo produto–receita com vigência; sub-receita Formulation→Formulation; Combo; estoque FG; modalidade mista.

---

## Lacunas confirmadas (contrato real)

1. Produto independente de receita (CRUD + API).
2. Modalidades `purchased` / `combo` / `mixed`.
3. Sub-receita como formulação aninhada (não só ingredient role).
4. Combos e composição comercial.
5. Estoque / lote de produto acabado e mercadoria comprada (além de ingredient 1:1).
6. Página e estados da jornada “Fluxo produtivo”.
7. Impressão gerencial distinta da operacional (mesmo endpoint hoje mistura risco).
8. Markup por família de produto (precedência produto → família → org).
9. Calculadora lateral contextual com memória auditável unificada no UX (backend de memória existe em costing).
10. Rastreio ponta a ponta FG → linha de NF em um único drill-down de UI.

---

## Fluxos exatos (entrada → saída)

### 1) Ingrediente novo → fornecedor → compra → recebimento → lote → estoque

| Etapa | Entrada | Ação | Saída | Responsável | Estado hoje | Bloqueios | Próxima | Tela reuso | Ausente |
|---|---|---|---|---|---|---|---|---|---|
| Cadastro | dados ingrediente | criar Ingredient | SKU interno | compras/qualidade | completo | org | vincular fornecedor | ingredientes | — |
| Fornecedor | supplier + item | cadastrar | SupplierItem | compras | completo | — | cotar/pedir | fornecedores | — |
| Compra | PR/PO | emitir | PO aberto | compras | completo | aprovação | receber | compras | — |
| Recebimento | NF + linhas | receber | lots + moves | estoque | completo | PO/qty | inventário | recebimentos | histórico preço NF unificado UI |
| Estoque | lot | disponível | saldo | estoque | completo | quarantine | produção/venda | lotes/estoque | — |

### 2) Produto comprado → recebimento → estoque → venda/uso

| | | | | | | | | | |
|---|---|---|---|---|---|---|---|---|---|
| Cadastro produto | atributos comerciais | criar Product purchased | product_id | comercial | **ausente** | — | receber | — | CRUD produto |
| Recebimento | NF | receber em InventoryItem do produto | lot FG/mercadoria | estoque | **ausente** (só ingredient) | — | venda | recebimentos parcial | item não-ingrediente |
| Uso/venda | pedido | baixa | move | PDV/ops | **ausente** no Panne | — | — | — | canal venda |

### 3) Produto produzido → receita → ordem → execução → acabado

| | | | | | | | | | |
|---|---|---|---|---|---|---|---|---|---|
| Produto | cadastro | modalidade produced | product | comercial | parcial | — | vincular receita | — | CRUD |
| Receita | composição | versionar/aprovar | formulation_version | P&D | completo | aprovação | planejar | receitas | vínculo vigente explícito |
| Ordem | produto ou receita | criar OP | order | PCP | completo | insumos | executar | ordens | origem “só produto” canônica |
| Execução | order | apontar | events/yield | cozinha | completo | etapas | encerrar | executar | — |
| FG | good_units | estocar | lot FG | estoque | **ausente** | — | rotular/vender | — | depósito FG |

### 4) Sub-receita → intermediário → consumo final

| | | | | | | | | | |
|---|---|---|---|---|---|---|---|---|---|
| Definir | sub-formulation | referenciar na final | BOM aninhado | P&D | **parcial/ambíguo** | ciclos | OP filha | receitas | FK formulation |
| Produzir | OP filha | executar | intermediário | cozinha | parcial (deps) | deps | consumir | ordens/deps | estoque intermediário |
| Consumir | final | pick/consume | baixa | cozinha | parcial | disponibilidade | FG final | execução | contrato claro |

### 5) Combo → disponibilidade → separação → entrega

Todo o fluxo: **ausente** (modelo + API + UI).

### 6) Alteração de receita → nova versão → vigência

| | | | | | | | | | |
|---|---|---|---|---|---|---|---|---|---|
| Editar | versão atual | nova version | draft | P&D | completo | OP abertas | aprovar | receitas | |
| Vigência | approve | ativar | vigente por contexto | P&D | **parcial** | conflito | OPs novas | — | ProductRecipeLink |
| Histórico | versions | listar | auditoria | P&D | completo | — | — | receitas | UI vínculo produto |

### 7) Custo real → markup/margem → preço

| | | | | | | | | | |
|---|---|---|---|---|---|---|---|---|---|
| Custo | events + prices | calcular | memória | gestão | completo | perms | preço | custos | |
| Markup | regra | aplicar | preço calc | gestão | completo | — | publicar | precos | família |
| Margem | preço/custo | indicar | % | gestão | completo | — | — | | calculadora lateral UX |

### 8) Rastreabilidade FG → NF

Backend tem lotes, moves, receipts e production events — **parcialmente** encadeáveis.  
UI de drill-down único FG→OP→consumo→lote→receipt_line: **ausente**.

---

## Contratos que existem mas não cobrem o modelo 028

- `InventoryItem` estritamente 1:1 com ingrediente.
- Criação de produto técnico só via receita.
- Impressões sem perfil “sem financeiro” vs “com financeiro” no contrato da API.
- Assistente e quadro não guiam a jornada 1–8.
