# Evidência R026-003 — Lista de ordens (2ª passagem)

## Validação Cortex 1ª

Aprovado: colunas, unidade, links acessíveis, `from_status`, Executar em pesagem.
Reprovado: `Produto ausente` / `Plano sem código legível` em todas as linhas.

## Causa dos fallbacks

API Uvicorn da demo **sem reload**; processo antigo sem campos `product`/`plan`. Frontend já esperava o contrato novo.

## Reinício

1. `stop-demo.ps1` + confirmação portas `5080`/`5180` livres
2. `start-demo.ps1` → `/health` e `/ready` ok
3. `GET …/production/orders` como `demo-owner` / Panne Demonstração

### Amostra sanitizada (sem credenciais)

```json
{
  "public_code": "ORD-20260824-0004",
  "status": "in_weighing",
  "product": { "code": "PAO-FR", "display_name": "Pão francês (Demo)" },
  "plan": { "public_code": "PLN-20260824-0004" },
  "target_mode": "mass",
  "target_quantity": "3300.000000"
}
```

Sem chaves de custo/preço no payload. Detalhe da mesma ordem: mesmos `product`/`plan`.
Padaria Horizonte Demo: `0` ordens; sem overlap de `public_code` com a Panne.

## JOIN

`outerjoin(TechnicalProduct, id + organization_id)` + `outerjoin(ProductionPlan, …)`.
FK `technical_product_id` NOT NULL + org composta = produto sempre presente sob integridade; `product: null` só se join falhar (teste de órfão).

## Matriz Executar

Ver `orderListActions.ts` / `REVISAO-PROPRIETARIO-026.md`: Executar só em released / in_weighing / ready / in_progress / on_hold (+ permissão).
