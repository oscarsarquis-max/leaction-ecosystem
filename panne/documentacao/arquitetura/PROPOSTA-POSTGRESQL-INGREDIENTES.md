# Proposta relacional PostgreSQL — ingredientes

**Status:** realizada no PostgreSQL da Panne em `0002_ingredient_catalog` (modelos em `app/modules/ingredient_catalog/models.py`). Sem APIs, sem ficha, sem `formula_ingredient`. Sem dados reais.

## Decisões na realização

| Pendência | Decisão |
|---|---|
| Catálogo global na v1 | Global só para unidade, nutriente, alergênico e fonte oficial. Ingrediente é sempre organizacional. |
| `organization_ingredient` | **Colapsada.** `ingredient.organization_id` + unique parcial `(organization_id, code)` onde `active`. |
| `current_version_id` | **Omitida.** Vigente = única linha `ingredient_version.status = 'published'` (índice único parcial). |
| Preparação reutilizada | Capacidade criada em `ingredient_composition.role = 'preparation'`. Sem fórmula ainda. |
| Precisão | Massa/qtde/nutriente `numeric(14,6)`; fator SI/conversão `numeric(20,10)`; preço `numeric(14,4)`. |
| Base nutricional oficial | `per_100g` é a base canônica do dossiê. Outras bases permitidas no check. |
| Fornecedor | `supplier_item.ingredient_id` (sem tabela de adesão). `supplier_party_id` sem FK (identidade ainda não existe). |
| Preço | `supplier_item_price` criada (histórico; rethink de `tbl_ingrediente_compra`). |

---

Texto original da proposta (referência). A realização segue este desenho, com os desvios da tabela acima.

Convenções: `snake_case`; PK `uuid`; tempo `timestamptz` UTC; grandezas `numeric` com escala; FK e checks no banco; JSONB só se a estrutura não for estável — **não usado nesta proposta**.

Auditoria comum (todas as tabelas de negócio): `created_at timestamptz not null`, `created_by uuid null`, `updated_at timestamptz not null`, `updated_by uuid null`. Identidade de usuário ainda não existe; colunas reservadas.

Status de ciclo: `situation text` com check `in ('active','cancelled')` onde couber, em vez de copiar `CADASTRADO`/`CANCELADO`.

---

### `measurement_unit`

- **Finalidade:** unidade canônica (substitui `tbl_medida` + `varchar` de unidade).
- **Colunas:** `id uuid`, `code text`, `name text`, `plural_name text`, `dimension text`, `si_factor numeric(20,10) not null` (fator para a unidade SI da dimensão), `symbol text`.
- **Tipos:** `dimension` check `in ('mass','volume','count','energy','arbitrary')`.
- **PK:** `id`.
- **FK:** nenhuma.
- **Restrições:** `code` unique; `si_factor > 0`.
- **Índices:** unique `code`.
- **Auditoria:** padrão.
- **Versionamento:** cadálogo; alteração rara (melhor nova linha que editar fator publicado).
- **Escopo:** global.

### `unit_conversion`

- **Finalidade:** conversão explícita quando o fator SI não basta (ex. unidade culinária contextual).
- **Colunas:** `id uuid`, `from_unit_id uuid`, `to_unit_id uuid`, `factor numeric(20,10)`, `context text null`.
- **PK:** `id`.
- **FK:** `from_unit_id`, `to_unit_id` → `measurement_unit`.
- **Restrições:** `from_unit_id <> to_unit_id`; `factor > 0`; unique `(from_unit_id, to_unit_id, context)`.
- **Índices:** unique acima.
- **Versionamento:** nenhum (fator contextual versionado só se `context` citar uma versão — pendente).
- **Escopo:** global.

### `nutrient_definition`

- **Finalidade:** catálogo de nutrientes (em vez de colunas fixas).
- **Colunas:** `id uuid`, `code text`, `name text`, `unit_id uuid`, `group_code text`.
- **PK:** `id`.
- **FK:** `unit_id` → `measurement_unit`.
- **Unique:** `code`.
- **Escopo:** global.
- **Versionamento:** código estável; nome pode corrigir sem novo id.

### `allergen`

- **Finalidade:** catálogo (inclui glúten e lactose como códigos).
- **Colunas:** `id uuid`, `code text`, `name text`.
- **PK / unique:** `id` / `code`.
- **Escopo:** global.

### `data_source`

- **Finalidade:** origem do dado (norma, tabela, laudo, fabricante).
- **Colunas:** `id uuid`, `source_type text`, `title text`, `external_ref text`, `valid_from date`, `valid_to date`, `uri text`, `organization_id uuid null`.
- **Check:** `source_type in ('official_catalog','regulation','manufacturer_label','lab_report','internal_calc','user_declared')`; `valid_to is null or valid_to >= valid_from`.
- **Escopo:** global se `organization_id` nulo; senão organizacional.
- **Versionamento:** vigência por datas, não por overwrite.

### `ingredient`

- **Finalidade:** identidade do insumo.
- **Colunas:** `id uuid`, `organization_id uuid not null`, `code text not null`, `display_name text not null`, `is_additive boolean not null default false`, `situation text not null`, `current_version_id uuid null`.
- **PK:** `id`.
- **FK:** `current_version_id` → `ingredient_version` (deferrable, para inserção em duas etapas) **ou** omitir e resolver vigente por query — **pendente**.
- **Unique:** `(organization_id, code)` where `situation = 'active'`.
- **Índices:** `(organization_id, display_name)`.
- **Versionamento:** identidade estável; dossiê em `ingredient_version`.
- **Escopo:** organizacional.

### `ingredient_version`

- **Finalidade:** dossiê técnico imutável após publicação.
- **Colunas:** `id uuid`, `ingredient_id uuid not null`, `version_no int not null`, `status text not null`, `work_unit_id uuid not null`, `data_source_id uuid`, `notes text`, `published_at timestamptz`, `superseded_at timestamptz`, `review_state text`.
- **Check:** `status in ('draft','published','superseded')`; `version_no >= 1`; `review_state in ('pending','approved','rejected')`.
- **PK:** `id`.
- **FK:** `ingredient_id` → `ingredient`; `work_unit_id` → `measurement_unit`; `data_source_id` → `data_source`.
- **Unique:** `(ingredient_id, version_no)`.
- **Índice parcial:** uma linha `published` por `ingredient_id`.
- **Auditoria:** padrão + `published_by`.
- **Versionamento:** esta é a tabela de versão.
- **Escopo:** o da organização do ingrediente.

### `ingredient_composition`

- **Finalidade:** compostos / preparação como filho.
- **Colunas:** `id uuid`, `parent_version_id uuid`, `child_version_id uuid`, `quantity numeric(14,6)`, `unit_id uuid`, `sort_order int`, `role text`.
- **Check:** `quantity > 0`; `sort_order >= 0`; `role in ('constituent','preparation')`; `parent_version_id <> child_version_id`.
- **PK:** `id`.
- **FK:** ambas as versões → `ingredient_version`; `unit_id` → `measurement_unit`.
- **Unique:** `(parent_version_id, child_version_id)`; `(parent_version_id, sort_order)`.
- **Escopo:** herdado da versão.
- **Ciclo:** impedir ciclo na aplicação; check SQL não cobre grafo N níveis.

### `ingredient_nutrient`

- **Finalidade:** valor nutricional de uma versão.
- **Colunas:** `id uuid`, `ingredient_version_id uuid`, `nutrient_id uuid`, `value numeric(14,6)`, `value_unit_id uuid`, `basis text`, `data_source_id uuid null`.
- **Check:** `basis in ('per_100g','per_100ml','per_portion','per_unit')`; `value >= 0`.
- **PK:** `id`.
- **FK:** versão, `nutrient_definition`, unidades, `data_source`.
- **Unique:** `(ingredient_version_id, nutrient_id, basis)`.
- **Escopo:** organizacional via versão.

### `ingredient_allergen`

- **Finalidade:** declaração alergênica da versão.
- **Colunas:** `id uuid`, `ingredient_version_id uuid`, `allergen_id uuid`, `presence text`, `is_override boolean not null default false`, `override_reason text`.
- **Check:** `presence in ('contains','may_contain','absent','unknown')`; se `is_override` então `override_reason` not null.
- **Unique:** `(ingredient_version_id, allergen_id)`.
- **FK:** versão, `allergen`.

### `organization_ingredient`

- **Finalidade:** adesão local (nome de estoque, situação operacional). Omitir na v1 se colapsar em `ingredient`.
- **Colunas:** `id uuid`, `organization_id uuid`, `ingredient_id uuid`, `local_code text`, `local_name text`, `situation text`.
- **Unique:** `(organization_id, ingredient_id)`; `(organization_id, local_code)`.
- **Escopo:** organizacional.

### `supplier_item`

- **Finalidade:** SKU de fornecedor + unidade de compra.
- **Colunas:** `id uuid`, `organization_ingredient_id uuid`, `supplier_party_id uuid`, `sku text`, `purchase_unit_id uuid`, `situation text`.
- **FK:** adesão; unidade; `supplier_party_id` fica pendente do módulo de identidade (não criar tabela de pessoa agora).
- **Unique:** `(organization_ingredient_id, supplier_party_id, sku)`.
- **Histórico de preço (filho sugerido, não detalhado):** `supplier_item_price (id, supplier_item_id, captured_at, quantity numeric(14,6), unit_price numeric(14,4), currency char(3))` — rethink de `tbl_ingrediente_compra`.

### `formula_ingredient` — só fronteira

Não criar agora. Quando existir fórmula: `formula_version_id`, `ingredient_version_id`, `gross_mass numeric(14,6)`, `net_mass numeric(14,6)`, `correction_factor numeric(8,4)`, `sort_order int`, custos como snapshot opcional. Check `gross_mass >= net_mass` quando ambos massa.

---

## O que não entra nesta proposta

- Tabelas de ficha, modo de preparo, porção, rótulo, produto comercial, usuário, empresa física.
- JSONB de nutrientes.
- Cópia de enums `F`/`T`.
- `serial` / `int` de negócio.

## Ordem realizada

1. `measurement_unit`, `unit_conversion`
2. `nutrient_definition`, `allergen`, `data_source`
3. `ingredient`, `ingredient_version` (sem FK circular: vigente por índice parcial)
4. `ingredient_composition`, `ingredient_nutrient`, `ingredient_allergen`
5. `supplier_item`, `supplier_item_price` — sem `organization_ingredient`
