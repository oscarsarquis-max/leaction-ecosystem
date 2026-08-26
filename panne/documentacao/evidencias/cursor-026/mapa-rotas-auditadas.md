# Mapa de rotas auditadas — CURSOR-026

- Saúde: 200 ambiente=demo
- Prontidão: 200
- Organização: Panne Demonstração (45104a8c-d590-5946-b8dd-f5534e89e338)
- IDs reais: ingrediente=0c2d415d-1f7a-4107-ab42-1d4a19fcc8af receita=e16051da-97d4-4db8-b6b3-ebc02b1cce33 ordem=0b86090a-25c2-4fc0-9065-947d3f5bcaf4

## Perfis

- demo-owner: HTTP 200 — Proprietário Demo
- demo-manager: HTTP 200 — Gestor de Produção Demo
- demo-formulator: HTTP 200 — Formulador Demo
- demo-baker: HTTP 200 — Padeiro Demo
- demo-reviewer: HTTP 200 — Revisor Regulatório Demo
- demo-buyer: HTTP 200 — Compras Demo
- demo-reader: HTTP 200 — Leitor Demo

## Domínios vivos

- ingredientes: HTTP 200 · 18 registros
- receitas: HTTP 200 · 6 registros
- ordens: HTTP 200 · 10 registros
- planos: HTTP 200 · 10 registros
- quadro: HTTP 200 · 10 registros
- dossies: HTTP 200 · 2 registros
- custos: HTTP 200 · 2 registros
- lotes: HTTP 200 · 6 registros
- posicao: HTTP 200 · 6 registros
- reservas: HTTP 200 · 2 registros
- requisicoes: HTTP 200 · 4 registros
- cotacoes: HTTP 200 · 2 registros
- pedidos: HTTP 200 · 2 registros
- recebimentos: HTTP 200 · 2 registros
- devolucoes: HTTP 200 · 1 registros
- relatorios: HTTP 200 · 10 registros

## Rotas abertas no produto

- `/entrar` — Entrar na Panne (público) — frontend HTTP 200
- `/inicio` — Início (autenticado) — frontend HTTP 200
- `/producao` — Quadro de produção (production.board.read) — frontend HTTP 200
- `/planejamento` — Planejamento (production.plan.read) — frontend HTTP 200
- `/ordens` — Ordens (production.order.read) — frontend HTTP 200
- `/rastreabilidade` — Rastreabilidade (production.traceability.read) — frontend HTTP 200
- `/componentes/ingredientes` — Ingredientes (ingredient.read) — frontend HTTP 200
- `/componentes/estoque` — Estoque (inventory.read) — frontend HTTP 200
- `/componentes/estoque/posicao` — Posição de estoque (inventory.read) — frontend HTTP 200
- `/componentes/lotes` — Lotes e validade (inventory.read) — frontend HTTP 200
- `/componentes/fornecedores` — Fornecedores (supplier.read) — frontend HTTP 200
- `/receitas` — Receitas (recipe.read) — frontend HTTP 200
- `/conformidade` — Conformidade (labeling.read) — frontend HTTP 200
- `/gestao/custos` — Custos (costing.read) — frontend HTTP 200
- `/gestao/compras/necessidades` — Necessidades (procurement.read) — frontend HTTP 200
- `/gestao/compras/requisicoes` — Requisições (procurement.read) — frontend HTTP 200
- `/gestao/compras/cotacoes` — Cotações (procurement.read) — frontend HTTP 200
- `/gestao/compras/pedidos` — Pedidos (procurement.read) — frontend HTTP 200
- `/gestao/compras/recebimentos` — Recebimentos (procurement.receive) — frontend HTTP 200
- `/gestao/compras/devolucoes` — Devoluções (procurement.return) — frontend HTTP 200
- `/gestao/inventarios` — Inventários (inventory.count) — frontend HTTP 200
- `/gestao/relatorios` — Relatórios (reporting) — frontend HTTP 200
