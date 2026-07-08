-- Produto de assinatura PanelDX (planos CRM / vitrine)
INSERT INTO products (sku, name, type, external_resource_id)
VALUES (
    'PANELDX_SUBSCRIPTION',
    'Assinatura PanelDX',
    'PANELDX_SUBSCRIPTION',
    'paneldx_crm_planos'
)
ON CONFLICT (sku) DO UPDATE SET
    name = EXCLUDED.name,
    type = EXCLUDED.type,
    external_resource_id = EXCLUDED.external_resource_id;
