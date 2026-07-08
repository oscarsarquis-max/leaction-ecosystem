-- Produto add-on de licenças PanelDX (pacotes extras de usuários)
INSERT INTO products (sku, name, type, external_resource_id)
VALUES (
    'PANELDX_ADDON',
    'Pacote Extra de Usuários PanelDX',
    'PANELDX_ADDON',
    'paneldx_addon_licencas'
)
ON CONFLICT (sku) DO UPDATE SET
    name = EXCLUDED.name,
    type = EXCLUDED.type,
    external_resource_id = EXCLUDED.external_resource_id;
