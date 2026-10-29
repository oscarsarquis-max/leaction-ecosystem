# Inventário do backoffice

29/10/2026. Leitura de código local, saúde pública e disco do Hub. Sem navegação administrativa.

## Módulos da API

Montagem em `backend/app/api/v1/__init__.py`: saúde, operações, fidelidade, admin, catálogo, agenda pública, vitrine/pedidos, Gigio, biblioteca, conta e acompanhamentos.

Admin em `backend/app/api/v1/admin/__init__.py`:

| Prefixo | Arquivo | Função observada |
|---|---|---|
| autenticação | `admin/auth.py` | Login, sessão, ativação de senha |
| `/admin/ops` | `admin/ops.py` | Agenda de produção, alertas, saúde de atendimento, outbox, Web Push |
| `/admin/orders` | `admin/orders.py` | Lista, detalhe, aceite, data, produção, pronto, entrega, conclusão, cancelamento, adaptação, nota |
| `/admin/products` e mídia | `admin/products.py` | Catálogo e arquivos |
| `/admin` agenda e receitas | `admin/schedule.py` | Bases, massas, semana, fechamentos, pão sob encomenda, ingredientes |
| vitrine | `admin/showcase.py` | Posições |
| solicitações de data | `admin/date_requests.py` | Fila e aceite comercial |
| receitas da semana | `admin/week_recipes.py` | Editorial |
| Gigio | `admin/gigio.py` | Notas e harmonização |
| acompanhamentos | `admin/accompaniments.py` | Ofertas espelhadas do Hub |

Interface em `frontend/src/admin/AdminApp.tsx` (menu nas linhas 562–574): Pedidos, Produtos, Agenda, Fidelidade. Dentro de Produtos, `CatalogTabs.tsx` acrescenta receitas, Gigio, harmonizações e complementos. Resumo e agenda só quando a rota é a de pedidos (`ordersHome`, a partir da linha 594).

## Entidades reaproveitáveis

| Entidade | Onde | O que guarda | O que não guarda |
|---|---|---|---|
| `Order` | `models/orders.py:36` | Estado, endereço, modalidade, data, reserva, entrega, totais, `order_kind` standard/redemption | Organização, vendedor fiscal, tarefas de parceiro |
| `OrderItem` | `models/orders.py:149` | Produto ou massa/formato, quantidade, snapshots de nome e preço, `physical_units` | Produtor, rendimento de kit, embalagem de componente |
| `OrderStatusHistory` | `models/orders.py:279` | Transição e autoria | Dimensão logística separada |
| `PaymentRecord` | `models/payments.py:12` | Tentativa, valores, método Pix/cartão, ID do provedor, erro saneado | Participação de parceiro, saldo liberado, repasse |
| `PaymentIntegrationEvent` | mesmo arquivo | Evento do Hub, idempotência, resultado | Livro contábil |
| `ProductionBatch` | `models/production.py:20` | Janela, prazo e `capacity_units` | Lote de ingrediente, validade, produtor externo |
| `FulfillmentSlot` | `models/production.py:64` | Janela de retirada ou entrega da fornada | Roteiro multi-ponto |
| `Product` / `ProductVariant` | `models/products.py:52` e `:127` | Publicação, preço, disponibilidade | Versão de composição de kit |
| `AccompanimentItem` | `models/accompaniments.py:22` | Snapshot de oferta do Hub (`hub_source` padrão `mercadolivre`) | Parceiro operacional, embalagem, tarefa |
| `AdminAccount` / `AdminSession` | `models/admin.py:38` e `:10` | Uma conta e sessões com expiração e revogação | Organização e perfil |

## Identidade

`login_admin` (`domain/admin_auth.py:151`) só aceita o usuário igual a `settings.admin_username` (linha 168), com senha da conta armazenada, limite de tentativas e sessão com CSRF. `AdminPrincipal` (linha 75) traz usuário, sessão e CSRF. Não há organização nem papel de operação. Não há segundo fator no fluxo lido.

A tabela `admin_accounts` existe. O login não escolhe uma conta entre várias organizações; compara com o usuário configurado.

## Pedido e pagamento

Envio em `storefront_orders.py`. Pão regular com data e sem adaptação é aceito por `system:auto-accept` (linhas 743–749). Caso com avaliação permanece `submitted`. `start_checkout` (linha 1056) recusa cobrança antes do aceite (linha 1076). `physical_units` copia a unidade física da variante ou a quantidade do pão encomendado (linhas 147 e 209). Isso reserva capacidade; não calcula rendimento de um pão para vários kits.

Produção sem quitação existe como exceção explícita em `domain/orders.py:333`, com motivo registrado. Confirmar entrega é ação própria. Pagamento não inicia produção.

Estados operacionais: `draft`, `submitted`, `confirmed`, `in_production`, `ready`, `completed`, `cancelled` (`models/enums.py:4`). Financeiro à parte: `pending`, `paid`, `failed`, `cancelled`, `partially_refunded`, `refunded`, `unknown`.

Não há rota administrativa de estorno no inventário de `app/api`. Estorno aparece como estado que a observação do provedor pode aplicar, não como mesa de contestação.

## Efeitos de leitura

`GET /admin/products` chama `fill_empty_showcase_slots` (`api/v1/admin/products.py:56–63`). A função (`domain/showcase.py:78`) pode esvaziar slot de produto não publicado e preencher slots vazios. `get_db` (`db/session.py:36–42`) confirma a sessão ao terminar a requisição sem exceção. Abrir a listagem de produtos pode alterar a vitrine pública.

`GET /api/v1/health` não acessa o banco (`api/v1/health.py:14`). `GET /api/v1/ready` executa `SELECT 1` numa conexão direta, sem passar por `get_db`. Em 29/10/2026 ambos responderam 200 com `{"status":"ok","service":"lojadepaes"}`.

Consulta de pagamento no Hub que reconcilia continua fora desta auditoria: não foi chamada.

## Workers no processo da API

`main.py` linhas 76–83 iniciam, no mesmo processo, o worker de e-mail, o de Web Push e o de verificação financeira. O financeiro usa lote 10, intervalo 30 segundos, prioridade de pendências e solta o bloqueio da linha antes da consulta HTTP. Isso está no código local e foi exercido em `lojadepaes_test` (ver [matriz-regressoes-e-validacao.md](matriz-regressoes-e-validacao.md)). Não há medição de produção com várias réplicas.

## Integrações

| Integração | Papel atual | Limite |
|---|---|---|
| Hub Pay, app da Loja | Uma cobrança de valor por tentativa, Pix ou cartão, outbox e consulta | `app_id` da Loja não é identidade de parceiro. Split não está no fluxo de amount checkout examinado |
| Mercado Pago, via Hub | Provedor da cobrança | Habilitação de split 1:N da conta não foi consultada. Documentação oficial de 29/10/2026 condiciona 1:N a carteira assessorada |
| E-mail operacional e Web Push | Avisos administrativos, com deduplicação | Não são canal de parceiro |
| WhatsApp | Link manual da home; canal automático registrado como desligado | Não é operação de parceiro |
| Acompanhamentos | Oferta externa espelhada para a vitrine | Não é venda, logística nem repasse de parceiro de food service |
| Gigio | Atendimento e harmonização | Não coordena produção distribuída |

## O que a execução confirmou hoje

Hub: os três hashes do relatório estão no disco e o processo `gateway-api` pid `591861` foi iniciado em 28/10/2026 17:46:41. Loja: saúde pública ok; imagem e Alembic da instância não foram relidos porque a porta 22 não respondeu e abri-la estava fora do escopo.

`readme/current-state.md` ainda descreve publicações de 27/10 e anteriores. O relatório `prompt-105a` descreve `prod-20261028c` e Alembic `d5e9f2a18b33`. São documentos diferentes. Nenhum dos dois substitui uma inspeção nova da imagem.
