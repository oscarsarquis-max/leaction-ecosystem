-- PRM_009 — identidades fixas da demonstração pública.
-- Não reutiliza Loja de Pães (624023a4-57e3-415c-b7d0-925ca1acd3b7).
-- Membership do operador já autorizado no AF público é acrescentada só nesta empresa.
-- Não executar até autorização de apply. Sem convite automático.

INSERT INTO actionfinance.tenant (id, code, name, active, created_at, updated_at, version)
VALUES (
    '9c2e0a10-4f11-4b8a-9c2e-0a104f110009',
    'af-public-test',
    'ActionFinance teste público',
    true,
    now(),
    now(),
    1
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO actionfinance.company (
    id, tenant_id, code, name, active, is_demo, business_timezone, created_at, updated_at, version
)
VALUES (
    '9c2e0a10-4f11-4b8a-9c2e-0a104f11000c',
    '9c2e0a10-4f11-4b8a-9c2e-0a104f110009',
    'af-public-test-padaria',
    'Padaria de teste público',
    true,
    true,
    'America/Sao_Paulo',
    now(),
    now(),
    1
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO actionfinance.pay_company_mapping (
    id, tenant_id, company_id, pay_app_id, environment, authorized, created_at, updated_at
)
VALUES (
    '9c2e0a10-4f11-4b8a-9c2e-0a104f110801',
    '9c2e0a10-4f11-4b8a-9c2e-0a104f110009',
    '9c2e0a10-4f11-4b8a-9c2e-0a104f11000c',
    'af-public-test-padaria',
    'HOMOLOG',
    true,
    now(),
    now()
)
ON CONFLICT (tenant_id, company_id) DO UPDATE
SET pay_app_id = EXCLUDED.pay_app_id,
    environment = EXCLUDED.environment,
    authorized = true,
    updated_at = now();

-- company_membership: o mesmo user_id OPERATOR já autorizado no AF público
-- recebe uma linha nova só nesta empresa. Sem ADMIN global e sem alterar
-- a membership da Loja (624023a4-57e3-415c-b7d0-925ca1acd3b7).
-- Resolução no apply:
--   SELECT user_id FROM actionfinance.company_membership
--   WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7'
--     AND role = 'OPERATOR' AND status = 'ACTIVE'
-- e INSERT em company_membership para 9c2e0a10-4f11-4b8a-9c2e-0a104f11000c.
-- Sem e-mail, sem convite Cognito.
