# Lotes e validade

O lote preserva item, org, estabelecimento, local, lote interno, lote do fornecedor, fornecedor, fabricação, validade, recebimento, unidade, quantidade recebida, estado e hash.

Estados: `available`, `quarantined`, `blocked`, `expired`, `exhausted`, `closed`.

Validade ausente não é inferida. Lote vencido, bloqueado ou em quarentena exige `inventory.expired.override` e justificativa.
