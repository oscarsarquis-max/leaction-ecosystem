# Permissões e RLS de estoque

Permissões distintas de `inventory.*`, `procurement.*` e `reporting.inventory.read`. Cognito e `legacy_role_label` não autorizam.

Padeiro: ler e separar. Não aprova ajuste nem compra. Gestor de produção: operação, sem ajuste/aprovação de compra. Comercial: compras + leitura de estoque. Owner/admin/técnico: conjunto completo.

RLS ENABLE+FORCE, default deny, isolamento A/B, runtime sem fallback administrativo.
