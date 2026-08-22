# Matriz legado → Panne — fichas e nutrição

Confronta o DDL legado com o catálogo já existente (`ingredient`, `ingredient_version`, catálogos globais) e com os conceitos novos. Sem implementação neste ciclo.

## Preservar

Conhecimentos válidos do legado, a reexpressar com FKs e versão.

| Conhecimento | Onde estava | Destino proposto |
|--------------|-------------|------------------|
| Escopo por empresa | `ID_EMPRESA` | `organization_id` |
| Identidade de receita distinta do nome do produto | `NOME_RECEITA` + `ID_PRODUTO` | `formulation` + opcional `technical_product` |
| Linha com bruto, líquido e fator de correção | `tbl_ficha_tecnica_ingrediente` | `formulation_item` |
| Totais de massa e custo no cabeçalho | `PESO_*`, `CUSTOS_*` | Derivados ou cache de `scale_calculation` / evidência — não fonte |
| Rendimento e cocção | `RENDIMENTO*`, `FATOR_COCCAO`, `PESO_COZIDO`, `PERDA_GANHO` | Cabeçalho de `formulation_version` + motor de cálculo |
| Tempo de preparo / cocção | `time` | `process_step` (duração) e/ou metadados da versão |
| Texto de modo de preparo | `MODO_PREPARO` | `process_step` ordenado |
| Escala para outra quantidade | `tbl_ficha_tecnica_porcao*` | `scale_calculation` (derivado, não cópia permanente de linhas) |
| Porção e medida caseira no rótulo | `PORCAO`, `MC_*` | Entrada de `nutrition_calculation` |
| Declaração de ingredientes e alergênicos | textos + flags | Derivado + override documentado no snapshot |
| Responsável técnico (campo) | `RESPONSAVEL_TECNICO` | Evento `approval` + papel, não só string |
| Situação / bloqueio | `SITUACAO`, `BLOQUEADO` | Status de ciclo da versão (`draft` / `published` / `superseded`) |
| Permissão de módulo | `PER_FICHA_TECNICA`, `PER_ROTULAGEM_NUTRICIONAL` | Papéis em `organization_membership` (futuro; não neste ciclo) |
| Distinção preço comercial vs custo técnico | `tbl_produto_preco` vs custos da ficha | Custo fora do dossiê de conformidade; preço comercial à parte |

## Repensar

Útil, mas modelagem inadequada.

| Tema | Problema no legado | Direção |
|------|--------------------|---------|
| Produto polimórfico `USO_*` | Um registro mistura insumo, ficha e rótulo | Separar `ingredient`, `formulation`, `technical_product`, documento, rótulo |
| Duas composições | Ficha e nutrição sem FK cruzada | Fonte única: `formulation_version` |
| Nome/código copiados na linha | Snapshot informal | Apontar `ingredient_version`; denormalizar só em snapshot de documento |
| `FC` e totais `float` | Precisão e origem opacas | `numeric` + evidência do cálculo |
| `RENDIMENTO` int vs `RENDIMENTO_RECEITA` varchar | Dois conceitos no mesmo cabeçalho | Separar unidades produzidas, massa final e texto de apresentação |
| Porção como cópia de linhas | Duplica composição | Recalcular a partir da versão |
| Nutrientes em colunas + `varchar` | Sem catálogo, sem regra | `nutrient_definition` + itens calculados |
| Glúten/lactose manuais | Podem mentir sobre a composição | Derivação + override com motivo |
| `OBSERVACAO` int | Tipo opaco | Texto ou catálogo tipado |
| PK typo / tabela sem PK | Integridade frágil | UUID + unique de negócio |
| Impressão como flag de usuário | Documento não versionado | `technical_document` + `label_snapshot` |
| Custo na linha da ficha | Mistura conformidade e comercial | Snapshot de custo opcional, fora da imutabilidade nutricional |

## Descartar

| Item | Motivo |
|------|--------|
| Flags `USO_*` no mesmo agregado | Polimorfismo sem justificativa no novo domínio |
| Segunda lista `tbl_info_nutricional_ingrediente` como fonte | Duplicação; vira projeção |
| Colunas fixas de macros no cabeçalho | Catálogo já existe |
| `KCAL`/`KJ`/`PERC_VD` como `varchar` fonte da verdade | Formatação pertence ao snapshot |
| `QUANTIDADE__` | Artefato |
| `tbl_pop*` como documento da ficha | Outro domínio (POP operacional) |
| `tbl_lancamento_docs` | Financeiro |
| Grade `VD_*` / `BC_*` no dossiê técnico | Comercial |
| Soft-delete `CANCELADO` como único histórico | Versão + `audit_event` |
| Sobrescrita in-place da ficha | Versões publicadas imutáveis |
| Charset `latin1` / `float` | Convenções da Panne |
| Senha e dados de acesso de `tbl_usuario` | Já separados em `app_user` |

## Criar

| Lacuna | Conceito |
|--------|----------|
| Identidade estável da receita | `formulation` |
| Versão publicável imutável | `formulation_version` |
| Linha ligada a versão de insumo | `formulation_item` → `ingredient_version` |
| Etapas ordenadas | `process_step` |
| Escala determinística | `scale_calculation` |
| Ensaio / piloto | `trial`, `trial_measurement` |
| Aprovação formal | `approval` |
| Produto técnico (acabado) | `technical_product` |
| Cálculo nutricional derivado | `nutrition_calculation`, `nutrition_calculation_item` |
| Documento preliminar vs aprovado | `technical_document` |
| Rótulo congelado | `label_snapshot` |
| Memória de cálculo | `calculation_evidence` |
| Referência bibliográfica da receita | `recipe_reference` (liga `data_source` / biblioteca) |
| Sem alteração retroativa | Trigger/regra como em `ingredient_version` |
| IA ≠ cálculo oficial | Tipo de evidência / origem `suggestion` vs `official` |

## Conceitos da Panne × legado

| Conceito | Legado | Responsabilidade | Relações | Invariantes | Versão | Escopo |
|----------|--------|------------------|----------|-------------|--------|--------|
| `RecipeReference` | Ausente (só nome/código) | Ligar formulação a obra/fonte | `formulation` → `data_source` | Fonte vigente explícita | Metadados da fonte | Org ou global da fonte |
| `Formulation` | Parcial: `tbl_ficha_tecnica` identidade | Quem é a receita | Org, opcional produto técnico | Código único ativo por org | Não (identidade) | Organizacional |
| `FormulationVersion` | Ausente (sobrescrita) | Estado técnico publicável | Itens, etapas, aprovações | Uma `published` vigente; imutável | Sim | Org via formulação |
| `FormulationItem` | `tbl_ficha_tecnica_ingrediente` | Composição oficial | → `ingredient_version` + unidade | Filho publicado; qtde > 0; ordem | Congela com a versão | Org |
| `ProcessStep` | Texto em `modo_preparo` | Etapas | Versão | Ordem única | Congela com a versão | Org |
| `ScaleCalculation` | Cópia `porcao*` | Recalcular para N | Versão + parâmetros | Determinístico; evidência | Resultado versionado | Org |
| `Trial` | Ausente | Piloto / ensaio | Versão ou rascunho | Não altera publicado | Identidade do ensaio | Org |
| `TrialMeasurement` | Ausente | Medida observada | Trial + unidade | Separar observado de calculado | Não | Org |
| `Approval` | Ausente (só usuário/data) | Evento formal | Alvo versionado + `app_user` | Append-only | Evento | Org |
| `TechnicalProduct` | Parte de `tbl_produto` | Acabado técnico | 0..N formulações | Não é SKU comercial | Identidade | Org |
| `NutritionCalculation` | `tbl_info_nutricional` (paralelo) | Cálculo oficial | Versão + porção | Derivado; não editar à mão a composição | Sim (imutável se oficial) | Org |
| `NutritionCalculationItem` | Colunas + tabela varchar | Nutriente calculado | → `nutrient_definition` | Base explícita | Congela | Org |
| `TechnicalDocument` | Ausente (impressão) | Ficha/PDF derivado | Versão + status doc | Preliminar ≠ aprovado | Sim | Org |
| `LabelSnapshot` | Textos + tabela | Rótulo congelado | Cálculo + regras + fontes | Imutável após aprovação | Snapshot | Org |
| `CalculationEvidence` | Ausente | Memória de cálculo | Cálculo + `data_source` | Append-only | Evento | Org |

O catálogo já criado **não** recebe bruto/líquido/FC/rendimento (ver `FRONTEIRAS-FUTURAS-FORMULA.md`). `ingredient_composition` continua sendo a árvore do **insumo**, não a ordem do rótulo do pão.
