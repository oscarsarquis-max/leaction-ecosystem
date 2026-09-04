# Modelo canônico Produto–Receita–Combo

**Ciclo:** CURSOR-028-A · decisões fechadas em 028-B.  
**Status:** canônico.  
**Decisões vinculantes:** ver `ESPINHA-DORSAL-FLUXO-PRODUTIVO.md`.

## 1. Produto

Identidade comercial/operacional. **Não exige receita.**

### Atributos canônicos

| Grupo | Campos |
|---|---|
| Identidade | código, nome, família, situação (rascunho/ativo/inativo) |
| Unidades | unidade de estoque, unidade de venda, conteúdo/peso, embalagem |
| Conservação | validade padrão / regra de shelf-life |
| Natureza | final \| intermediário |
| Abastecimento | `produced` \| `purchased` \| `combo` \| `mixed` |
| Preço | política (própria / herdada família / org), histórico |
| Rastreio | histórico de alterações versionado |

### Modalidades

| Modalidade | Receita | Ordem de produção | Composição comercial |
|---|---|---|---|
| Produzido | Opcional (necessária para OP “normal”) | Sim | Não |
| Comprado | Não | Não | Não |
| Combo | Não | Não | Sim (lista de produtos) |
| Misto | Opcional | Condicional | Não |

### Compatibilidade com o código atual

- Hoje existe `TechnicalProduct` criado como efeito colateral de `POST /recipes`.
- Não existe CRUD de produto comercial independente.
- **Canônico (028-B):** `TechnicalProduct` **evolui** para Produto (modalidade + atributos comerciais), desacoplando a criação da receita. **Sem** entidade `Product` concorrente.

## 2. Receita (Formulation)

Definição **versionada** de transformação produtiva.

### Atributos canônicos

| Grupo | Campos |
|---|---|
| Versão | número/código, vigência (início/fim), status (rascunho/aprovada/obsoleta) |
| Rendimento | quantidade, unidade, perdas planejadas |
| Composição | ingredientes + **sub-receitas** (referência a outras formulações) |
| Processo | etapas, equipamentos, tempos, temperaturas, controles |
| Resultado | produto resultante **opcional** (final, intermediário ou componente) |
| Governança | aprovação, autor, motivo de nova versão |

### Regras

- Receita sem produto resultante é válida (teste, preparo sem SKU comercial).
- Receita com produto resultante não “é” o produto; apenas o produz.
- Sub-receita: consumo de rendimento de outra formulação (não inventar “ingrediente fantasma” permanente).
- Ciclos de sub-receita proibidos.

### Compatibilidade

- `Formulation` + `FormulationVersion` + itens + etapas: **reaproveitáveis**.
- Role `preparation` hoje aponta para `ingredient_id` — **ambíguo** frente a sub-receita real.
- Dependências de OP (`ProductionOrderDependency`) existem; falta composição Formulation→Formulation.

## 3. Vínculo produto–receita

| Regra | Detalhe |
|---|---|
| Opcional | Produto comprado/combo sem vínculo |
| Versionado | Liga produto ↔ versão de receita (não só “receita”) |
| Vigência | Uma definição **vigente por organização + estabelecimento + intervalo temporal** |
| Histórico | Alternativas históricas preservadas |
| Combo | **Não** usa este vínculo para composição comercial |

API conceitual: `ProductRecipeLink { product_id, formulation_version_id, organization_id, establishment_id, valid_from, valid_to, priority }`.

## 4. Combo

Composição versionada de **produtos**, não de ingredientes.

| Campo | Descrição |
|---|---|
| produto-combo | Identidade do combo (modalidade `combo`) |
| componentes | produto_id + quantidade + unidade |
| substituições | lista opcional permitida |
| disponibilidade | regra (todos disponíveis / parcial) |
| custo | derivado dos componentes (snapshot + real) |
| preço | **próprio** (não obrigatoriamente soma) |
| montagem | instrução curta de expedição (texto), sem etapas de produção |
| restrições | sem ciclos; sem consumo direto de ingredientes |

Estoque: **combo virtual por padrão** — reserva/baixa apenas dos **componentes**. Sem SKU de estoque do combo no piloto.

## 5. Modalidade mista

Um único produto com identidade, estoque e histórico únicos, abastecido por compra **ou** produção conforme política.

### Regras propostas

| Tema | Regra |
|---|---|
| Identidade | Um `product_id`; flags `allow_purchase` + `allow_produce` |
| Estoque | Um saldo FG; origem do lote discrimina `purchase` vs `production` |
| Custo | Lote traz custo unitário da origem (NF ou ordem) |
| Abastecimento | **Decisão explícita por evento** (compra ou produção) — sem auto-escolha implícita |
| Rastreabilidade | Movimentação registra documento de origem (receipt_line ou production_order) |
| Receita | Só obrigatória quando a via escolhida é produção |

## 6. Relação com inventário atual

| Conceito canônico | Entidade atual | Gap |
|---|---|---|
| Ingrediente | `Ingredient` | — |
| Item de estoque (insumo) | `InventoryItem` 1:1 ingrediente | Não cobre produto FG/comprado/combo |
| Lote | `InventoryLot` | — |
| Fornecedor / preços | `Supplier`, `SupplierItem`, `IngredientPrice` | — |
| Compra / recebimento | PR→RFQ→PO→Receipt | — |
| Produto | `TechnicalProduct` | Sem modalidade, sem CRUD, acoplado à receita |
| Receita | `Formulation*` | Sub-receita real incompleta |
| Combo | — | Ausente |
| FG | `good_units` na ordem | Sem depósito FG |

## 7. Decisões fechadas (não reabrir sem ADR)

| Tema | Decisão |
|---|---|
| Receita vigente | Organização + estabelecimento + vigência |
| Entidade produto | Evoluir `TechnicalProduct` → Produto |
| Misto | Decisão explícita por abastecimento |
| Combo | Virtual por padrão |
| Família | Entidade organizacional |
| Intermediário | Produto (não duplicar como Ingrediente) |

## Exemplos mapeados

### Bolo de chocolate
- Produto final `Bolo de chocolate` (produzido).
- Receita final vN: 500 g massa-base (sub-receita), 200 g cobertura (sub-receita), 4 morangos, etapas de montagem.
- Sub-receitas podem gerar OP dependentes ou estoque intermediário.

### Pão carioca
- Produto + uma receita direta (sem sub-receita obrigatória).

### Coxinha
- Produto + receita final referenciando receitas de massa e recheio.

### Suco engarrafado
- Produto `purchased`: fornecedor, SKU, NF, lote, validade, preço compra/venda; sem receita/OP.

### Combo café da manhã
- Produto `combo`: 1 pão produzido + 1 suco + 1 manteiga; preço próprio; custo derivado; sem receita.
