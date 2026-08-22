# Política de numeração pública

Códigos imutáveis, únicos por organização.

- Plano: `PLN-YYYYMMDD-NNNN` (data operacional).
- Ordem: `ORD-YYYYMMDD-NNNN` (data operacional do plano, ou início previsto, ou hoje).
- Batelada: `{codigo_ordem}-Bnn`.

Contador `production_code_counter` com `SELECT … FOR UPDATE`. Não usa `MAX+1` sem lock. Colisão entre organizações não vaza código alheio (único é `(organization_id, public_code)`).
