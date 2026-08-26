# ADR — Seed reference, demo e smoke

## Decisão

Separar três camadas:

1. **Reference** — catálogos canônicos (unidades, nutrientes, alergênicos). Idempotente. Sem personas.
2. **Demo** — cenário sintético completo no banco isolado `panne_demo`.
3. **Smoke** — o mesmo construtor em recorte de jornada, em `panne_smoke` ou transação efêmera.

Alembic permanece `0020_inventory_procurement`. Não há migração `0021`.

## Por quê

O produto precisa de interface populada para auditar o assistente e o quadro, sem contaminar o banco lógico `panne` e sem dados reais.

## Consequências

- Scripts recusam `panne`, `production` e sufixo inválido.
- Demo usa serviços de domínio. Inserção direta só em catálogo sem comando.
- IA somente via `FakeModelGateway`.
