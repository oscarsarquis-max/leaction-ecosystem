#!/usr/bin/env bash
set -euo pipefail

# E2E checkout: PanelDX proxy -> Hub gateway -> simular pagamento -> webhook PanelDX
PANELDX_BASE="${PANELDX_BASE:-https://paneldx.com.br}"
HUB_API="${HUB_API:-https://api.actionhub.com.br}"
TEST_EMAIL="${TEST_EMAIL:-dev@leaction.com.br}"
TEST_ID_MATU="${TEST_ID_MATU:-}"
TEST_SKU="${TEST_SKU:-PANEL_MATURIDADE}"

echo "==> 1) Config pagamentos via proxy PanelDX"
curl -sk "${PANELDX_BASE}/hub-api/config/payments" | head -c 400
echo ""

if [[ -z "$TEST_ID_MATU" ]]; then
  echo "TEST_ID_MATU obrigatorio para fulfillment completo"
  exit 2
fi

PAYLOAD=$(cat <<EOF
{
  "client_id": "paneldx",
  "sku": "${TEST_SKU}",
  "amount": 1,
  "id_matu": "${TEST_ID_MATU}",
  "customer": { "email": "${TEST_EMAIL}", "name": "E2E Test" },
  "webhook_url": "${PANELDX_BASE}/api/hub/payment-webhook",
  "hub_public_url": "https://actionhub.com.br",
  "return_to": "/projeto"
}
EOF
)

echo "==> 2) POST /hub-api/v1/payments (via PanelDX)"
CREATE_RES=$(curl -sk -w "\nHTTP:%{http_code}" -X POST "${PANELDX_BASE}/hub-api/v1/payments" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$CREATE_RES"
HTTP=$(echo "$CREATE_RES" | tail -1 | sed 's/HTTP://')
BODY=$(echo "$CREATE_RES" | sed '$d')
ORDER_ID=$(echo "$BODY" | node -pe "try{JSON.parse(require('fs').readFileSync(0,'utf8')).payment_id}catch(e){''}" 2>/dev/null || true)

if [[ "$HTTP" != "201" ]] || [[ -z "$ORDER_ID" ]]; then
  ORDER_ID=$(echo "$BODY" | grep -oE '"payment_id":"[^"]+"' | head -1 | cut -d'"' -f4)
fi

if [[ -z "$ORDER_ID" ]]; then
  echo "Falha ao criar pedido"
  exit 1
fi
echo "ORDER_ID=$ORDER_ID"

echo "==> 3) Simular pagamento no Hub"
SIM_RES=$(curl -sk -w "\nHTTP:%{http_code}" -X POST "${HUB_API}/simular-pagamento" \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"${ORDER_ID}\"}")
echo "$SIM_RES"

echo "==> 4) Status do pedido no Hub"
curl -sk "${HUB_API}/orders/${ORDER_ID}/checkout?email=${TEST_EMAIL}" | head -c 500
echo ""
