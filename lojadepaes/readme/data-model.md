# Modelo de dados — Loja de Pães

Identificadores de negócio: UUID. Nomes técnicos em inglês (`snake_case`). Textos de vitrine em português. Instantes em `TIMESTAMPTZ` (UTC). Fuso da padaria para calendário: `LOJADEPAES_BAKERY_TIMEZONE` (padrão `America/Sao_Paulo`).

Estados finitos: `VARCHAR` + `CHECK` (não ENUM nativo do PostgreSQL), para o Alembic alterar valores sem recriar tipos. Valores conhecidos estão em `app/models/enums.py`.

`created_at` / `updated_at`: `now()` no insert; `updated_at` em UPDATE via trigger `set_updated_at()` nas tabelas mutáveis. Updates SQL crus devem deixar o trigger correr (não desligar `session_replication_role`).

Dinheiro: inteiros em **centavos**, moeda `BRL`. `NULL` em preço/acréscimo = **não configurado**, não grátis.

## Diagrama

```mermaid
erDiagram
  dough_types ||--o{ dough_ingredient_compatibilities : allows
  ingredients ||--o{ dough_ingredient_compatibilities : allowed
  dough_types ||--o{ dough_shape_compatibilities : allows
  bread_shapes ||--o{ dough_shape_compatibilities : allowed
  ingredients ||--o{ pairing_tips : tip
  allergens ||--o{ dough_allergens : marks
  allergens ||--o{ ingredient_allergens : marks
  dough_types ||--o{ dough_allergens : marked
  ingredients ||--o{ ingredient_allergens : marked
  production_batches ||--o{ fulfillment_slots : windows
  production_batches ||--o{ production_batch_dough_limits : optional
  dough_types ||--o{ production_batch_dough_limits : capped
  fulfillment_slots ||--o{ orders : receives
  production_batches ||--o{ orders : bakes
  orders ||--o{ order_items : contains
  order_items ||--o{ order_item_ingredients : extras
  orders ||--o{ order_status_history : trail
  orders ||--o{ order_internal_notes : staff
  orders ||--o{ payment_records : finance
  payment_records ||--o{ payment_integration_events : events
  articles
  inspiration_posts
  media_assets ||--o{ products : featured
  products ||--o{ product_ingredients : composition
  products ||--o{ product_variants : offers
  products ||--o{ product_events : audit
  ingredients ||--o{ product_ingredients : optional_ref
```

## Produtos padrão da padaria

Tabelas novas: `media_assets`, `products`, `product_ingredients`, `product_variants`, `product_events`.

- `products.editorial_status`: `draft` | `published` | `archived`. `is_available` é disponibilidade manual, independente do estado editorial.
- `product_ingredients` é lista informativa de composição (nome + ordem). `catalog_ingredient_id` pode apontar a um ingrediente do assistente, mas **não** torna a composição uma inclusão selecionável.
- `product_variants.presentation_type`: `weight` (peso líquido em gramas) ou `pack` (unidades por embalagem). Preço em centavos da variação inteira, não por grama. Rascunho pode ter `price_cents` nulo; publicação exige preço > 0. Ausência de preço ≠ brinde.
- Foto destacada: arquivo em disco (`LOJADEPAES_MEDIA_DIR`, padrão `lojadepaes/var/media/`, fora do Git e fora de `frontend/images/`). O Postgres guarda só a referência (`media_assets`). Nomes internos são UUID. Não há exclusão física automática nesta versão; arquivos órfãos exigirão rotina futura de limpeza. Inclua o diretório no backup.
- Não apague produto ou variação: arquive/desative. `ON DELETE RESTRICT` na foto e no vínculo produto→variação.

## Extensão futura de `order_items` (não aplicada agora)

Hoje `order_items` representa só o pão personalizado (`dough_type_id` + `bread_shape_id` obrigatórios + inclusões). Produto padrão é outra origem e **não** deve ser simulado com uma massa/inclusão inventada.

No checkout (etapa posterior):

- cada item será **exclusivamente** personalizado **ou** produto padrão (variação), nunca os dois;
- quantidade comercial da variação (2 × pacote de 6 = 2 linhas/embalagens, 12 unidades físicas);
- snapshots de nome do produto, apresentação e preço da variação no momento da confirmação;
- totais do pedido calculados no servidor, sem aceitar o total enviado pelo navegador.

Capacidade da fornada **não** pode tratar um pacote com 6 unidades como uma unidade produzida. A relação comercial × produção × receitas do Panne será definida antes de aceitar pedidos reais desses produtos. A seleção local desta etapa não cria pedido nem reserva vaga.

## Políticas de exclusão

- Catálogo referenciado por pedido: `ON DELETE RESTRICT` (desative com `is_active`, não apague).
- Itens e histórico de um pedido: `CASCADE` a partir de `orders`.
- Eventos financeiros: `SET NULL` no `payment_record_id` se o registro for removido (não há operação de remoção nesta etapa).

## Capacidade

Ocupação = `SUM(order_items.quantity)` onde `orders.holds_capacity` é verdadeiro. Não há contador desnormalizado.

`holds_capacity` fica verdadeiro na confirmação e permanece:

- em `confirmed`, `in_production`, `ready` e `completed` (pães produzidos ou já planejados na fornada/janela não devolvem vaga);
- em `cancelled` **somente** se `production_started_at` estiver preenchido (produção já começou).

Cancelar um pedido ainda confirmado (antes da produção) zera `holds_capacity` e libera a reserva.

Confirmação: `app.domain.orders.confirm_order` — bloqueia pedido, depois fornada, depois janela (`FOR UPDATE`). Idempotente se o pedido já passou de `draft`. Cancelamento é idempotente (já cancelado) e exige motivo na primeira vez.

## Financeiro

Não há coluna de “pago” em `orders`. Quitação deriva de `payment_records` (`app.domain.payments.order_is_financially_settled`). Ausência de registro ≠ cobrança pendente no ActionHub.

## Conteúdo

`articles.body_markdown` é Markdown. Quando for à vitrine, renderizar com sanitização; não tratar HTML cru como confiável.

Alergênicos: `is_reviewed=false` por padrão. Linha ausente **não** significa “não contém”.
