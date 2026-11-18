# GESTAO-001 — Levantamento para a Loja de Pães – Gestão (só leitura)

Data: 2026-11-02 · Escopo: leitura. Nada foi alterado na Loja, na produção, no banco, no Caddy ou no DNS. Nenhum SQL foi executado. Nenhum dado pessoal foi lido ou é citado aqui.

## 0. Objetivo

Preparar o terreno para o **Loja de Pães – Gestão** (`gestao.lojadepaes.com.br`). É um app novo, separado da Loja, com código em `C:\Projetos\lojadepaes-gestao`, dados próprios e login próprio. Ele lê a Loja (pedidos, fornadas, produtos) por um usuário Postgres somente leitura. Roda em contêiner próprio no mesmo Lightsail e entra no Caddy com um bloco novo.

### Executado (somente leitura) × Proposto (não executado)

| Executado, só leitura | Proposto, **não** executado |
|---|---|
| Leitura de código e config em `C:\Projetos\lojadepaes` (models, domínio, infra, scripts, frontend). | Todo SQL das seções 1 e 2. |
| AWS `get`/`list`/`describe`: Lightsail (instância, bundles, firewall, métricas, snapshots) e Route 53 (zona e registros). | Compose, bloco Caddy, comandos de deploy e rollback da seção 3. |
| Resolução DNS pública (`gestao.lojadepaes.com.br` não resolve hoje). | Registro DNS da seção 3.3. |
| — | Comandos de medição no host da seção 4.2, para o Oscar rodar. |

Limites desta rodada:

- Não entrei por SSH. Abrir a porta 22 exige `open-instance-public-ports`, que é escrita.
- **Rede Docker, nome do contêiner, memória e disco livres do host não foram observados.** Aparecem abaixo como inferência ou como comando proposto.

---

## 1. O que o Gestão vai ler da Loja

Origem: `backend/app/models/*.py` e `backend/app/domain/*.py` da Loja.

### 1.1 Tabelas e colunas úteis

Os pedidos têm colunas pessoais: `customer_*`, `delivery_*`, `customer_note`, `access_token_hash`, `identity_subject_id`, `crm_id_sessao`, `submit_idempotency_key` e `fidelity_*`. O Gestão **não** precisa delas e o `GRANT` da seção 2 não as expõe.

Toda tabela também tem `id`, e a maioria tem `created_at` e `updated_at`.

| Tabela | Colunas úteis para o Gestão | Para que serve |
|---|---|---|
| `orders` | `id`, `public_reference`, `status`, `fulfillment_modality`, `production_batch_id`, `production_local_date`, `requested_date`, `proposed_production_date`, `holds_capacity`, `order_kind`, `subtotal_cents`, `delivery_fee_cents`, `discount_cents`, `total_cents`, `currency`, `confirmed_at`, `cancelled_at`, `production_started_at`, `ready_at`, `completed_at`, `fulfilled_at`, `delivery_confirmed_at` | Cabeçalho do pedido, estado e data de produção. |
| `order_items` | `order_id`, `product_id`, `product_variant_id`, `dough_type_id`, `bread_shape_id`, `recipe_base_id`, `quantity`, `physical_units`, `dough_name_snapshot`, `shape_name_snapshot`, `net_weight_grams`, `unit_price_cents`, `line_total_cents` | Linhas. Ou item de catálogo (`product_id` + `product_variant_id`), ou item do Criador (`dough_type_id` + `bread_shape_id`), pelo check `ck_order_items_origin`. |
| `order_item_ingredients` | `order_item_id`, `ingredient_id`, `name_snapshot`, `surcharge_cents` | Inclusões e farinha escolhidas no Criador. |
| `order_item_adaptations` | `order_item_id`, `status` (sem `customer_text`) | Só para sinalizar adaptação pendente. É opcional e fica fora da v1. |
| `products` | `name`, `slug`, `recipe_base_id`, `editorial_status`, `is_available` | Produto vendável. |
| `product_variants` | `product_id`, `display_name`, `presentation_type` (`weight` ou `pack`), `net_weight_grams`, `units_per_pack`, `physical_units`, `price_cents`, `is_active` | Variante: peso ou pacote e quantos pães físicos tem. |
| `product_ingredients` | `product_id`, `name`, `sort_order`, `catalog_ingredient_id` | Composição pública, que serve de ponto de partida para a receita técnica. |
| `dough_types` | `name`, `slug`, `creator_kind` (`preparation` ou `retired_mass`), `base_price_cents`, `recipe_base_id`, `is_active`, `fermentation_hours` | Tipo de massa do Criador. |
| `ingredients` | `name`, `slug`, `assistant_role` (`flour` ou `inclusion`), `surcharge_cents`, `is_active` | Catálogo de inclusões e farinhas do Criador. Não é o cadastro de insumos do estoque. |
| `bread_shapes` | `name`, `slug`, `is_active` | Formas do Criador. |
| `recipe_bases` | `code`, `name`, `is_active` | **Receita-base**: a massa-mãe que limita a agenda (`daily_base_limit`). |
| `schedule_settings` | `production_weekdays`, `daily_physical_limit`, `daily_base_limit`, `horizon_days`, `min_advance_hours`, `eligibility_mode`, `occupancy_enabled`, `reservation_policy` | Singleton (`id=1`): dias de produção e tetos. |
| `schedule_week_overrides` | `week_start`, `production_weekdays`, `daily_physical_limit`, `daily_base_limit`, `eligibility_mode` | Exceção por semana. |
| `schedule_date_overrides` | `local_date`, `open_state`, `daily_physical_limit`, `daily_base_limit`, `eligibility_mode` | Exceção por dia. |
| `schedule_eligible_bases` | `scope_kind` (`default`, `week`, `date`), `scope_id`, `recipe_base_id` | Quais receitas-base podem ser produzidas em cada escopo. |
| `schedule_closures` | `start_date`, `end_date`, `first_eligible_date`, `pause_intake`, `cancelled_at` (sem `internal_reason`, `public_notice`, `created_by`) | Fechamentos. |
| `production_batches` | `code`, `planned_start_at`, `breads_available_at`, `order_deadline_at`, `capacity_units`, `status` (`planned`, `open`, `closed`, `cancelled`) | Fornada legada. Ainda é usada como data alternativa quando `production_local_date` é nulo. |
| `production_batch_dough_limits` | `production_batch_id`, `dough_type_id`, `capacity_units` | Teto por massa na fornada legada. |
| `payment_records` | `order_id`, `financial_status` (`pending`, `paid`, `failed`, `cancelled`, `partially_refunded`, `refunded`, `unknown`), `expected_cents`, `amount_paid_cents`, `amount_refunded_cents`, `confirmed_at` (sem `pix_*`, `mp_payment_id`, `external_*`) | Só para exibir "pago" e "a receber". |
| `managerial_exclusions` | `subject_type` (`order` ou `date_request`), `subject_id`, `kind` (`test` ou `duplicate`), `reversed_at` | Pedido de teste ou duplicado, excluído da gestão. `reversed_at IS NULL` significa exclusão ativa. |
| `alembic_version` | `version_num` | Para o Gestão detectar mudança de schema da Loja (cabeça atual `e7b3c9a41d06`). |

Fora do escopo:

- `week_recipes*` é editorial. É a receita pública da semana, não ficha técnica.
- `fidelity_*`, `date_requests` e `customer_*` não entram na v1.

### 1.2 Significado de cada status

`orders.status` (CHECK da Loja: `draft`, `submitted`, `confirmed`, `in_production`, `ready`, `completed`, `cancelled`):

| Status | Rótulo no backoffice | Significado | `holds_capacity` |
|---|---|---|---|
| `draft` | — | Carrinho ou rascunho, ainda não enviado. | não |
| `submitted` | **Aberto** | Cliente enviou. A padaria ainda não aceitou e não há reserva. | não |
| `confirmed` | **Aceito** (e **Pago** quando há pagamento `paid`) | Padaria aceitou. A data de produção fica em `production_local_date`. | **sim**, definido no aceite |
| `in_production` | **Em produção** | Produção iniciada (`production_started_at`). | sim |
| `ready` | Pronto (legado) | Aguardando confirmação de entrega. | sim |
| `completed` | **Entregue** (com `delivery_confirmed_at`) ou **Finalizado** | Ciclo encerrado. | liberado |
| `cancelled` | **Cancelado** | Cancelado. Libera a reserva, salvo se a produção já começou. | não |

- **"Pago" não é status do pedido.** É uma trilha derivada de `payment_records` (via `classify_payment`). Um pedido pago continua `confirmed`.
- Na produção os pagamentos estão desligados (`LOJADEPAES_PUBLIC_PAYMENTS_ENABLED=false`, conforme o `.env.production.example`). Hoje **aceito** é o único sinal de compromisso.

### 1.3 O que é demanda confirmada (proposta)

Regra que acompanha a da Loja (`domain/schedule.py::committed_for_date`):

- `orders.status IN ('confirmed','in_production','ready')`. Isso cobre aceito, pago (que é aceito com pagamento) e em produção. `ready` é legado e fica por segurança.
- `orders.holds_capacity = true`.
- Fora: `cancelled`, `draft`, `submitted` (aberto, fica como "demanda provável" separada) e pedidos com `managerial_exclusions` ativa.
- `completed` fica **fora da demanda futura**. Entra só em consultas de **produzido e realizado** (histórico e custo), por parâmetro. Assim o Gestão não esconde o que já foi feito.
- Data da fornada: `production_local_date`. Se for nulo, usa a data local de `production_batches.breads_available_at` (a Loja faz igual). Fuso: `America/Sao_Paulo` (`bakery_timezone`, default no `config.py`).
- Unidades: `COALESCE(order_items.physical_units, order_items.quantity)`.
  - `physical_units` já é o total da linha (variante × quantidade).
  - Vem **nulo** quando a variante não informa quantos pães físicos tem. O Gestão deve mostrar "unidades a confirmar" e **não somar zero em silêncio**.

### 1.4 SELECT proposto: demanda por fornada (não executado)

```sql
-- Demanda confirmada por fornada: data · produto/variante (ou massa do Criador) · quantidade
-- Parâmetros: :de, :ate (datas locais)
SELECT
  COALESCE(o.production_local_date,
           (pb.breads_available_at AT TIME ZONE 'America/Sao_Paulo')::date)  AS fornada_data,
  CASE WHEN oi.product_id IS NOT NULL THEN 'catalogo' ELSE 'criador' END      AS origem,
  COALESCE(p.name, oi.dough_name_snapshot, dt.name)                           AS produto_ou_massa,
  COALESCE(pv.display_name, oi.shape_name_snapshot)                           AS variante_ou_forma,
  rb.code                                                                     AS receita_base,
  SUM(oi.quantity)                                                            AS quantidade,
  SUM(COALESCE(oi.physical_units, oi.quantity))                               AS paes_fisicos,
  COUNT(*) FILTER (WHERE oi.physical_units IS NULL AND oi.product_id IS NOT NULL) AS linhas_unidades_pendentes
FROM orders o
JOIN order_items oi              ON oi.order_id = o.id
LEFT JOIN products p             ON p.id  = oi.product_id
LEFT JOIN product_variants pv    ON pv.id = oi.product_variant_id
LEFT JOIN dough_types dt         ON dt.id = oi.dough_type_id
LEFT JOIN recipe_bases rb        ON rb.id = COALESCE(oi.recipe_base_id, dt.recipe_base_id)
LEFT JOIN production_batches pb  ON pb.id = o.production_batch_id
WHERE o.status IN ('confirmed','in_production','ready')
  AND o.holds_capacity IS TRUE
  AND NOT EXISTS (
        SELECT 1 FROM managerial_exclusions me
        WHERE me.subject_type = 'order' AND me.subject_id = o.id AND me.reversed_at IS NULL)
  AND COALESCE(o.production_local_date,
               (pb.breads_available_at AT TIME ZONE 'America/Sao_Paulo')::date)
      BETWEEN :de AND :ate
GROUP BY 1,2,3,4,5
ORDER BY 1,2,3,4;
```

Pontos de atenção:

- A query usa `oi.id`/`o.id` só no join. O role não precisa de nenhuma coluna pessoal.
- Para o Criador, as inclusões saem de `order_item_ingredients` (`name_snapshot`), em consulta separada: `item × inclusão × quantidade`.
- Se a Loja mudar o schema, a query quebra. O Gestão confere `alembic_version` na partida e acusa divergência (ver 2.4).

---

## 2. Banco da Loja

### 2.1 Onde roda o Postgres e como o Gestão chega nele

Fonte: `infra/docker-compose.prod.yml` (lido). Rede e nome do contêiner não foram observados.

- **Serviço `db`**: imagem `postgres:16-alpine`, banco e usuário `lojadepaes`, volume `pgdata`.
- A senha vem de docker secret (`/opt/lojadepaes/secrets/db_password`).
- Só tem `expose: 5432`. **Não há porta publicada no host.** O Postgres só é alcançável de dentro da rede do compose, como `db:5432`.
- O `POSTGRES_USER` do `initdb` é superusuário do cluster. Criar roles e bancos novos é possível sem tocar na aplicação.
- Compose em `/opt/lojadepaes/app/infra/` (diretório do projeto `infra`).
  - Rede padrão provável: **`infra_default`**.
  - Volume provável: `infra_pgdata`.
  - **Inferência, não verificada.** Comando de conferência na seção 4.2.
- Caminho do Gestão até o banco: o contêiner do Gestão entra na rede `infra_default` como **rede externa**. Daí enxerga `db:5432`. Isso não muda o compose da Loja.
- A mesma rede dá ao Caddy o caminho até `gestao-api:8090`, sem reiniciar o Caddy.

### 2.2 SQL proposto para `gestao_reader` (não executado)

Executar no host, como superusuário do cluster. Senha gerada na hora, fora do histórico do shell.

Princípios:

- Só `SELECT` nas tabelas do item 1.1.
- Em `orders`, **GRANT por coluna**, sem as colunas pessoais.
- Sem `ALTER DEFAULT PRIVILEGES`, sem `pg_read_all_data`, sem schema inteiro.
- Tabela nova da Loja não aparece para o Gestão até alguém conceder de propósito.

```sql
-- 1) No banco "postgres" do servidor
CREATE ROLE gestao_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT
  CONNECTION LIMIT 5 PASSWORD :'gestao_reader_pw';

ALTER ROLE gestao_reader SET default_transaction_read_only = on;
ALTER ROLE gestao_reader SET statement_timeout = '15s';
ALTER ROLE gestao_reader SET idle_in_transaction_session_timeout = '30s';

GRANT CONNECT ON DATABASE lojadepaes TO gestao_reader;

-- 2) Conectado em lojadepaes (\c lojadepaes)
GRANT USAGE ON SCHEMA public TO gestao_reader;

-- orders: apenas colunas não pessoais
GRANT SELECT (
  id, public_reference, status, fulfillment_modality, production_batch_id,
  production_local_date, requested_date, proposed_production_date,
  holds_capacity, order_kind, currency,
  subtotal_cents, delivery_fee_cents, discount_cents, total_cents,
  confirmed_at, cancelled_at, production_started_at, ready_at,
  completed_at, fulfilled_at, delivery_confirmed_at, created_at, updated_at
) ON orders TO gestao_reader;

-- payment_records: sem pix_*, mp_payment_id, external_*, idempotency_key
GRANT SELECT (
  id, order_id, financial_status, expected_cents, amount_paid_cents,
  amount_refunded_cents, currency, confirmed_at
) ON payment_records TO gestao_reader;

-- schedule_closures: sem internal_reason, public_notice, created_by, updated_by
GRANT SELECT (
  id, start_date, end_date, first_eligible_date, pause_intake, cancelled_at
) ON schedule_closures TO gestao_reader;

-- order_item_adaptations: sem customer_text, bakery_response, reason (opcional, fora da v1)
-- GRANT SELECT (id, order_item_id, status) ON order_item_adaptations TO gestao_reader;

-- Tabelas sem dado pessoal: SELECT inteiro
GRANT SELECT ON TABLE
  order_items, order_item_ingredients,
  products, product_variants, product_ingredients,
  dough_types, ingredients, bread_shapes, recipe_bases,
  schedule_settings, schedule_week_overrides, schedule_date_overrides,
  schedule_eligible_bases,
  production_batches, production_batch_dough_limits,
  managerial_exclusions, alembic_version
TO gestao_reader;
```

Cuidados e limites:

- `managerial_exclusions` tem `reason` e `author_ref` em texto livre. Se o Oscar preferir, trocar por GRANT por coluna (`subject_type`, `subject_id`, `kind`, `reversed_at`).
- `SELECT *` em `orders` falha de propósito. Isso protege contra vazamento acidental. O Gestão usa lista explícita de colunas.
- `public_reference` não é dado pessoal, mas identifica o pedido. Se não for necessário na tela, retirar do GRANT.
- No Postgres 16 o `PUBLIC` já tem `CONNECT` e `USAGE` no schema `public`. O `GRANT` explícito é documentação e proteção caso alguém revogue o `PUBLIC` depois.
- `REVOKE` da Loja não é necessário e não é proposto, para não mexer em privilégio existente.
- O dump da Loja (`pg_dump --no-owner`) inclui os GRANTs. Num restore em servidor novo a role `gestao_reader` precisa existir antes.

### 2.3 Onde ficam os dados do Gestão — recomendação

**Recomendo um banco separado, `gestao`, no mesmo servidor Postgres.** Com role dona própria (`gestao_app`) e `gestao_reader` só para ler `lojadepaes`.

| | Banco `gestao` separado (recomendado) | Schema `gestao` dentro de `lojadepaes` |
|---|---|---|
| Isolamento | Total. Nenhum `ALTER`, `DROP` ou migração do Gestão encosta na Loja. | Mesmo banco. Um erro de migração ou de privilégio afeta a Loja. |
| Alembic | Cadeia própria (`alembic_version` própria). | Compartilha o banco com a cadeia da Loja. |
| Backup e restore | Independente. Restaurar a Loja não volta o Gestão no tempo e vice-versa. | Acoplado: o `pg_dump` da Loja leva junto, e o restore da Loja reverte o Gestão. |
| JOIN com dados da Loja | **Não existe entre bancos** (sem dblink ou fdw). O app abre duas conexões e junta em Python ou grava snapshot. | JOIN direto possível. |
| Backup hoje | `backup-pg.sh` faz dump só de `-d lojadepaes`. O banco `gestao` **não entra**. Precisa script próprio (proposto em 3.2). | Já entraria no dump atual. |

Como o Gestão trabalha:

- O app usa duas conexões: leitura da Loja (`gestao_reader`) e leitura e escrita do `gestao` (`gestao_app`).
- Dados sensíveis para custo, como a **demanda que virou ordem de produção**, são copiados como **snapshot** para o banco `gestao`. O histórico não muda se a Loja alterar o pedido depois.
- O consumo de estoque e o custo se apoiam nesse snapshot, não na leitura ao vivo.

SQL proposto para criar o banco (não executado):

```sql
CREATE ROLE gestao_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  CONNECTION LIMIT 10 PASSWORD :'gestao_app_pw';
CREATE DATABASE gestao OWNER gestao_app ENCODING 'UTF8';
REVOKE ALL ON DATABASE gestao FROM PUBLIC;
GRANT CONNECT ON DATABASE gestao TO gestao_app;
-- gestao_reader NÃO recebe nada em "gestao".
```

### 2.4 Acoplamento com o schema da Loja

- A Loja evolui por Alembic (cabeça atual `e7b3c9a41d06`). Coluna removida ou renomeada quebra o Gestão.
- Mitigação proposta, sem alterar a Loja:
  - Na partida, o Gestão lê `alembic_version` e compara com a lista de cabeças que ele conhece.
  - Se divergir, mostra aviso e para de consumir os dados da Loja, em vez de calcular errado.
  - Uma consulta de verificação (`SELECT` com as colunas usadas, `LIMIT 0`) roda no `/ready` do Gestão.

---

## 3. Publicação

### 3.1 Como a Loja é publicada hoje

Fonte: `scripts/p109d-publish.ps1`, `p109d-backup-and-deploy.sh`, `p96-refresh-ssh.ps1`, `infra/*`.

1. **Build local** (máquina do Oscar): `docker build -t lojadepaes:prod-YYYYMMDDx .` e `docker save`. Não há build no host.
   - `Dockerfile` multi-stage: `node:20-alpine` constrói o frontend, `python:3.12-slim` roda a API como `appuser`.
   - Uvicorn: porta 8080, 2 workers.
2. **SSH**: `p96-refresh-ssh.ps1` usa AWS Lightsail para abrir a porta 22 ao /32 de quem publica (`open-instance-public-ports`). Depois faz `scp` do tar e do script para `ubuntu@52.15.107.86` e roda o script remoto.
3. **No host** (`p109d-backup-and-deploy.sh`):
   - `pg_dump` do banco da Loja para `/opt/lojadepaes/backups/lojadepaes-<stamp>.sql.gz`.
   - `docker load`.
   - Grava `LOJADEPAES_API_IMAGE=<tag>` em `/opt/lojadepaes/app/infra/.env`.
   - Roda `alembic upgrade head` num contêiner efêmero (`run --rm --no-deps`).
   - `up -d --force-recreate api`.
   - Loop de health e ready (16 × 3 s).
   - **Rollback automático** para a tag anterior (`restore_previous`) se o health falhar.
4. **Compose** `infra/docker-compose.prod.yml`: `caddy` (`caddy:2`, 80 e 443), `api` e `db`.
5. **Caddy** `infra/Caddyfile`: bloco `lojadepaes.com.br` com `reverse_proxy api:8080`, HSTS e `nosniff`. `www` redireciona para o apex. O arquivo é montado `:ro` como **arquivo único** (bind mount de arquivo).
6. Última imagem publicada: `lojadepaes:prod-20261102b` (rollback `prod-20261102a`).
7. Backups:
   - `backup-pg.sh` envia para `s3://lojadepaes-backup-253137917703/lojadepaes-pg/` (07:15 UTC, só o banco `lojadepaes`).
   - Autosnapshot do Lightsail às 07:00 UTC: 2026-11-01 e 2026-11-02 em `Success`.

### 3.2 Proposta: subir o Gestão sem interromper a Loja (não executado)

Princípio: **projeto compose separado**, contêiner novo, **nenhum** `up` ou `restart` nos serviços da Loja. O Caddy só recebe `reload` (graceful, sem derrubar conexões).

**Ordem:**

1. **DNS primeiro** (3.3). O Caddy só emite o certificado quando o nome resolve para o IP. Com TTL 300, esperar propagar.
2. **Banco**: criar `gestao_reader`, `gestao_app` e o banco `gestao` (seção 2). Em um `psql` dentro do contêiner `db`:
   `docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T db psql -U lojadepaes -d postgres -f -`.
   Isso só adiciona roles e um banco, não toca nos dados da Loja.
3. **Segredos** em `/opt/lojadepaes-gestao/secrets/app.env` (`chmod 600`, dono `ubuntu`), fora do git. Senhas geradas no host com `openssl rand -base64 32`.
4. **Imagem**: build local, `docker save`, `scp`, `docker load`, como a Loja. Tag `lojadepaes-gestao:prod-YYYYMMDDx`.
5. **Compose do Gestão**, em `/opt/lojadepaes-gestao/deploy/docker-compose.prod.yml`:

```yaml
name: lojadepaes-gestao
services:
  gestao-api:
    image: ${GESTAO_IMAGE:-lojadepaes-gestao:local}
    container_name: gestao-api
    restart: unless-stopped
    env_file: /opt/lojadepaes-gestao/secrets/app.env
    expose: ["8090"]
    mem_limit: 256m
    cpus: 0.75
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8090/api/v1/health')"]
      interval: 15s
      timeout: 5s
      retries: 5
    networks: [loja_net]
networks:
  loja_net:
    external: true
    name: infra_default   # CONFIRMAR com `docker network ls` antes
```

   Detalhes:
   - **Um worker** de uvicorn. O Gestão é de uso interno e baixa concorrência.
   - Porta 8090 só em `expose`, sem publicar no host.
   - Subir com `docker compose -f .../docker-compose.prod.yml up -d` só neste projeto.
   - Antes, rodar `alembic upgrade head` do Gestão em contêiner efêmero, só no banco `gestao`.
6. **Caddy**: acrescentar um bloco novo, sem tocar nos blocos da Loja:

```caddyfile
gestao.lojadepaes.com.br {
    encode gzip
    header {
        Referrer-Policy strict-origin-when-cross-origin
        X-Content-Type-Options nosniff
        Strict-Transport-Security "max-age=31536000"
        X-Robots-Tag "noindex, nofollow"
    }
    reverse_proxy gestao-api:8090
}
```

   Passos seguros no host:
   1. Copiar o `Caddyfile` atual para `Caddyfile.bak-<stamp>`.
   2. Acrescentar o bloco **gravando no mesmo arquivo** (`cat >> Caddyfile`). **Não** usar editor ou `sed -i` que troque o inode, porque o bind mount de arquivo único passaria a apontar para o arquivo antigo.
   3. Validar: `docker compose ... exec -T caddy caddy validate --config /etc/caddy/Caddyfile`.
   4. `docker compose ... exec -T caddy caddy reload --config /etc/caddy/Caddyfile` (graceful). **Não** usar `restart`.
   5. Conferir `https://gestao.lojadepaes.com.br/api/v1/health` e **também** `https://lojadepaes.com.br/api/v1/health` e `/ready`.
7. **Decisão do Oscar (toca na Loja):** o `infra/Caddyfile` do repositório da Loja não tem o bloco novo. No host o arquivo passa a divergir do repo. Duas saídas:
   - (a) Registrar o bloco também no Caddyfile versionado da Loja, em outro commit, com autorização explícita.
   - (b) Manter uma cópia em `lojadepaes-gestao/deploy/caddy/gestao.caddy` e registrar a divergência no README do Gestão.
   - Recomendo **(b) agora**: nada na Loja muda. O ponto fraco é que um deploy futuro da Loja que copie o Caddyfile do repo apagaria o bloco. Hoje os scripts de deploy não copiam o Caddyfile, só trocam a imagem.
8. **Backup do banco `gestao`** (script próprio, proposto, em `lojadepaes-gestao/deploy/backup-gestao.sh`): `pg_dump -U gestao_app -d gestao` para `s3://lojadepaes-backup-253137917703/gestao-pg/`, via cron, fora do horário do da Loja (por exemplo 07:30 UTC). O autosnapshot do Lightsail já cobre o disco inteiro.

**Rollback (não executado):**

- Gestão com defeito: `docker compose -f /opt/lojadepaes-gestao/deploy/docker-compose.prod.yml down`. A Loja não é afetada.
- Caddy com problema: restaurar `Caddyfile.bak-<stamp>` (também gravando no mesmo inode) e fazer `caddy reload`. Se o `validate` falhar no passo 3 do item 6, o `reload` nem é feito.
- Banco: `DROP DATABASE gestao; DROP ROLE gestao_app, gestao_reader;`. A Loja não depende dessas roles.
- DNS: remover o registro `gestao`. Não afeta o apex nem o `www`.
- Imagem: manter a tag anterior (`GESTAO_IMAGE`) e fazer `up -d` com ela.

### 3.3 DNS

- **Provedor: Amazon Route 53.**
  - Zona pública `Z04478628VQ84VS1J0YU`, `lojadepaes.com.br.`.
  - NS confirmados por resolução pública: `ns-832.awsdns-40.net`, `ns-1389.awsdns-45.org`, `ns-343.awsdns-42.com`, `ns-2011.awsdns-59.co.uk`.
- Registros existentes (só leitura):
  - `A` do apex e do `www` → `52.15.107.86` (TTL 300).
  - NS e SOA.
  - TXT `_amazonses` e 3 CNAMEs DKIM (SES).
  - Sem MX.
- `gestao.lojadepaes.com.br` **não existe** hoje (não resolve).
- **Registro proposto (não executado):** `A  gestao.lojadepaes.com.br  →  52.15.107.86`, TTL 300, na zona `Z04478628VQ84VS1J0YU`.
- Alternativa: `CNAME gestao → lojadepaes.com.br`. O `A` é mais simples e o IP é fixo (IP estático do Lightsail).
- O DNS **precisa existir antes** do bloco Caddy. Sem isso a emissão do certificado falha e o Caddy fica tentando.

---

## 4. Recursos do Lightsail

### 4.1 O que foi lido

- Instância `lojadepaes-app`, região `us-east-2`, zona `us-east-2a`.
  - Ubuntu 24.04, bundle `small_3_0`: **2 vCPU, 2 GB de RAM, 60 GB de disco**.
  - IP estático `52.15.107.86`.
  - 2 GB de swapfile, criado pelo `bootstrap-lightsail-host.sh`.
- **CPU, últimos 14 dias** (métricas Lightsail):
  - Média diária de **~1,2% a 1,4%**.
  - Pico diário máximo entre **8,9% e 32,6%**.
  - `BurstCapacityPercentage` mínimo **~99,97% a 100%**: a instância não consome crédito de burst.
  - `StatusCheckFailed` = 0.
- **Memória e disco livre: não disponíveis.** A API da AWS não expõe memória nem disco do SO para o Lightsail, e a documentação do repo não traz esses números. **Não foi possível medir sem SSH.**
- Referência de preço (bundles `get-bundles`): micro 1 GB US$ 7, small 2 GB US$ 12, medium 4 GB US$ 24.
- Firewall (achado de higiene, **nada alterado**): portas 80 e 443 abertas ao mundo. A porta 22 acumulou ~31 IPs /32, resíduo do `p96-refresh-ssh.ps1`, que abre e não fecha.

### 4.2 Conclusão e comandos de medição (propostos, para o Oscar rodar, só leitura)

**CPU: cabe com folga.** Média perto de 1% e burst intacto.

**Memória é o limite real.** Em 2 GB já rodam:

- Postgres 16.
- API da Loja com 2 workers uvicorn.
- Caddy.
- Docker e containerd.
- Sistema operacional.

Estimativa, **não medida**: uso base de 0,8 a 1,1 GB. Um contêiner do Gestão com 1 worker e `mem_limit: 256m` deve caber. A margem depende de quanto o Postgres e os workers da Loja realmente ocupam.

**Veredito provisório: cabe com 1 worker e `mem_limit` de 256 MB, desde que a memória disponível hoje seja ≥ ~500 MB.** Se `MemAvailable` ficar abaixo de ~400 MB, ou o swap estiver em uso constante, **não cabe com margem**. Nesse caso subir para o bundle `medium` (4 GB, +US$ 12/mês) ou reduzir os workers da Loja antes.

Comandos propostos para o Oscar, apenas leitura, em `ssh ubuntu@52.15.107.86`:

```bash
free -m
swapon --show
df -h /
docker stats --no-stream
docker system df
docker network ls
docker inspect $(docker ps -q) --format '{{.Name}} {{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml ps
```

Valores a observar:

- `MemAvailable`, uso de swap e espaço em `/`.
- O nome real da rede, para confirmar `infra_default`.

---

## 5. Padrão da Loja a copiar (nunca importar)

O Gestão **copia** o desenho para dentro do próprio repo. Não há `import` de `C:\Projetos\lojadepaes`, nem submódulo, nem workspace compartilhado.

### 5.1 Backoffice (frontend)

Em `lojadepaes/frontend/src/admin/shell/`:

- `AdminShell.tsx` (153 linhas): moldura da página.
  - Controla o drawer no mobile (`max-width: 959px`) e prende o foco com Tab.
  - Compõe sidebar e topbar.
- `AdminSidebar.tsx` (117 linhas) e `nav.ts` (88 linhas): menu em grupos (`NAV_GROUPS`: Operação, Produção, Catálogo, Conteúdo, Clientes...).
- `AdminTopbar.tsx` (206 linhas): barra superior, conta e avisos.
- `PageHeader.tsx` (19 linhas): `title`, `description?`, `actions?`.
- `Button.tsx` (20 linhas): variantes `primary`, `secondary` e `danger`, classes `admin-btn`.
- `Card.tsx` (10 linhas): `div.admin-card`.
- `StatusChip.tsx` (32 linhas): `stage` → classe de tom (`c-open`, `c-acc`, `c-paid`, `c-prod`, `c-del`, `c-can`, `c-warn`, `c-none`) + `label`.
- `tokens.css` (33 linhas): variáveis `--admin-*` sob `.admin-frame`.
  - Cores de superfície, tinta e linha.
  - Acento `#9a4a2e`.
  - Cores de estágio.
  - Fonte "DM Sans" e números tabulares.
- `shell.css` (599 linhas): estilos do shell, do chip, do botão e do card.

O que copiar: esses 8 componentes mais `tokens.css` e `shell.css`, renomeando o prefixo `admin-` para `gestao-` se quiser evitar confusão.

O que **não** copiar: `AdminApp.tsx` e telas de pedidos, produtos e agenda. São da Loja.

O Gestão deve ter **identidade visível própria** (nome "Gestão" no topo, acento ou cor distinta), para o operador não confundir as duas telas.

### 5.2 Versões (instaladas no ambiente da Loja)

| Peça | Declarado | Instalado |
|---|---|---|
| Python | 3.12 (imagem `python:3.12-slim`) | — |
| FastAPI | `>=0.115` | 0.141.1 |
| SQLAlchemy | `>=2.0.36` | 2.0.54 |
| Alembic | `>=1.14` | 1.20.0 |
| Pydantic | `>=2.10` | 2.13.5 |
| psycopg | — | 3.3.5 (driver `postgresql+psycopg`) |
| uvicorn | `[standard]` | 0.53.0 |
| argon2-cffi | — | 25.1.0 |
| React / React DOM | `^18.3.1` | 18.3.1 |
| Vite | `^6.0.7` | 6.4.3 |
| TypeScript | `^5.7.2` | 5.9.3 |
| Vitest | `^2.1.8` | 2.1.9 |
| Node (build) | imagem `node:20-alpine` | — |

Sem lockfile Python versionado. Para o Gestão, **fixar versões** (`==` ou arquivo de constraints) para o build ser reproduzível.

### 5.3 Como funciona o login do backoffice da Loja hoje

Fonte: `domain/admin_auth.py`, `api/v1/admin/auth.py`, `core/config.py`.

- **Conta**: usuário e senha de `LOJADEPAES_ADMIN_USERNAME` e `LOJADEPAES_ADMIN_PASSWORD_HASH` (**argon2**). Há também link de ativação (`domain/activation.py`) para definir a senha pela primeira vez.
- **Login**: `login_admin` compara o usuário com `hmac.compare_digest` e confere a senha. Se o usuário não existe, confere contra um hash fictício, para não vazar por tempo de resposta. Falha devolve a mesma mensagem genérica.
- **Rate limit**: `admin_login_attempts`, por usuário e IP. **5 falhas em 15 minutos** bloqueiam.
- **Sessão**:
  - Token aleatório de 32 bytes, guardado como HMAC-SHA256 em `admin_sessions`, com `LOJADEPAES_ADMIN_SESSION_SECRET` (mínimo 32 caracteres).
  - Cookie `lojadepaes_admin_session`, `HttpOnly`, `SameSite=Lax`, `Secure` em produção (`LOJADEPAES_COOKIE_SECURE=true`).
  - TTL de **8 horas**.
  - Pode ser revogada (`revoked_at`).
- **CSRF**: header `X-CSRF-Token`, comparado com HMAC por sessão.
- **Dev local sem senha**: `LOJADEPAES_ADMIN_LOCAL_PASSWORDLESS`, só em loopback e fora de `production`. Está desligado em produção.
- É **uma conta única de env**, não uma tabela de usuários. O ator no log é `admin:<usuário>`.

### 5.4 Recomendação de login para o Gestão

- **Reaproveitar o desenho, não o código nem o cookie.**
  - Argon2, sessão em tabela com HMAC, cookie `HttpOnly` + `Secure` + `SameSite=Lax` (ou `Strict`, já que é app interno), CSRF por header, rate limit por usuário e IP, TTL de 8 h.
  - Isso já está provado na Loja.
- **Cookie, segredo e tabelas próprios.**
  - Nome do cookie distinto (`gestao_session`).
  - Segredo de sessão diferente.
  - Tabelas de sessão no banco `gestao`.
  - Assim, a sessão da Loja não vale no Gestão e o contrário também não.
- **Tabela `usuarios` desde o início**, em vez de conta única de env.
  - Com `papel` (`dono`, `operador`, `somente_leitura`).
  - Quem lança entrada de estoque e quem só consulta custo não precisam do mesmo poder.
  - O ator aparece em toda movimentação (auditoria).
- **Criação do primeiro usuário** por comando de console no contêiner, com senha lida de stdin. Sem senha em env e sem `local_passwordless` em produção.
- **MFA (TOTP)**: opcional. Vale considerar na v1.5, porque o Gestão mostra custo e margem.
- Domínio separado já isola o cookie. **Não** usar `Domain=.lojadepaes.com.br` em nenhum cookie, para um subdomínio não ler o outro.

---

## 6. Estrutura proposta de `C:\Projetos\lojadepaes-gestao`

```text
lojadepaes-gestao/
├─ .gitignore                  # próprio
├─ .dockerignore
├─ README.md
├─ Dockerfile                  # multi-stage, mesmo padrão da Loja
├─ backend/
│  ├─ pyproject.toml           # versões fixadas
│  └─ app/
│     ├─ main.py
│     ├─ core/                 # config, segurança, sessão
│     ├─ db/                   # engine "gestao" (rw) e engine "loja" (ro)
│     ├─ models/               # modelos do Gestão (insumo, lote, receita, produção, custo)
│     ├─ loja_reader/          # SELECTs da Loja, contratos e checagem de schema
│     ├─ domain/               # regras: estoque, validade, custo, produção
│     └─ api/v1/
├─ database/
│  ├─ alembic.ini
│  └─ migrations/              # só o banco "gestao"; nunca toca "lojadepaes"
├─ frontend/
│  ├─ package.json
│  └─ src/
│     ├─ shell/                # cópia adaptada do shell da Loja
│     └─ features/
├─ deploy/
│  ├─ docker-compose.prod.yml  # projeto próprio
│  ├─ caddy/gestao.caddy       # bloco do subdomínio
│  ├─ sql/                     # gestao_reader.sql, gestao_db.sql (propostos)
│  ├─ backup-gestao.sh
│  └─ publish.ps1              # build local, save, scp, deploy e rollback
├─ scripts/
└─ docs/
   └─ retornos/
      └─ GESTAO-001-retorno.md
```

### `.gitignore` próprio (proposta)

```gitignore
.env
.env.*
!.env.example
**/secrets/
*.key
*.pem
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
node_modules/
dist/
.vite/
*.log
.DS_Store
Thumbs.db
var/
*.sql.gz
*.tar
```

### Isolamento no monorepo

- O monorepo (`C:\Projetos`, remoto `leaction-ecosystem`) já tem `.gitignore` raiz que ignora `.env*` (exceto `*.example`), `**/secrets/` e `dist/`. A pasta `lojadepaes-gestao/` **não** é ignorada. Só `.env` foi confirmado como ignorado.
- **A Loja (`lojadepaes/`) é versionada dentro do mesmo repositório.** Ela não tem `.git` próprio. Por isso:
  - Nenhum arquivo do Gestão deve cair fora de `C:\Projetos\lojadepaes-gestao\`.
  - Commits do Gestão devem listar só esse caminho (`git add lojadepaes-gestao/`).
  - O Gestão **não** edita `lojadepaes/`.
- **Nenhum import entre os dois**:
  - O Gestão lê a Loja só por SQL com `gestao_reader`.
  - O código copiado do shell vira arquivo do Gestão, sem referência de volta.
- **Segredos só no host**, em `/opt/lojadepaes-gestao/secrets/`. Nada de senha de banco nos scripts versionados (os SQL em `deploy/sql/` usam `:'variavel'`).
- **Regras do workspace que valem em todo push** (`AGENTS.md`):
  - Os scripts `sync-db-from-lan.ps1`, `infra/sync-ecosystem-db-from-lan.ps1` e `infra/open-leaction-db-lan.ps1` entram no commit quando alterados.
  - Este levantamento não os alterou.
- Observação de higiene, fora do escopo: na raiz de `C:\Projetos` há `_writetest2.tmp` e uma pasta `zijUlojd` soltas, e em `lojadepaes/` há `_tmp_p70b_*`. Não foram tocados.

---

## 7. Resumo das decisões que dependem do Oscar

1. Confirmar rede e memória do host (comandos da seção 4.2). Daí decidir entre ficar no `small` e subir para `medium`.
2. Banco `gestao` separado (recomendado) ou schema dentro da Loja.
3. Bloco Caddy: manter só no host (b, recomendado) ou também no Caddyfile versionado da Loja (a).
4. `managerial_exclusions.reason` e `public_reference` entram no GRANT ou não.
5. Se `completed` entra na demanda: recomendo que não, e que entre só no realizado.
6. Login: tabela `usuarios` com papéis desde a v1, e MFA agora ou depois.

Nada foi executado. Sem commit.
