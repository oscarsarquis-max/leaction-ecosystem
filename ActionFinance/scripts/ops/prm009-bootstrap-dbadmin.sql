INSERT INTO actionfinance.tenant (id, code, name, active, created_at, updated_at, version)
VALUES (
    '9c2e0a10-4f11-4b8a-9c2e-0a104f110009',
    'af-public-test',
    'ActionFinance teste publico',
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
    'Padaria de teste publico',
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

INSERT INTO actionfinance.company_membership (
    id, user_id, tenant_id, company_id, role, status, created_at, updated_at, version
)
SELECT
    '9c2e0a10-4f11-4b8a-9c2e-0a104f110901',
    cm.user_id,
    '9c2e0a10-4f11-4b8a-9c2e-0a104f110009',
    '9c2e0a10-4f11-4b8a-9c2e-0a104f11000c',
    'OPERATOR',
    'ACTIVE',
    now(),
    now(),
    1
FROM actionfinance.company_membership cm
WHERE cm.company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7'
  AND cm.role = 'OPERATOR'
  AND cm.status = 'ACTIVE'
ON CONFLICT (user_id, tenant_id, company_id) DO NOTHING;

SELECT 'tenant=' || count(*) FROM actionfinance.tenant WHERE id = '9c2e0a10-4f11-4b8a-9c2e-0a104f110009';
SELECT 'company=' || count(*) FROM actionfinance.company WHERE id = '9c2e0a10-4f11-4b8a-9c2e-0a104f11000c';
SELECT 'mapping=' || count(*) FROM actionfinance.pay_company_mapping WHERE company_id = '9c2e0a10-4f11-4b8a-9c2e-0a104f11000c';
SELECT 'membership=' || count(*) FROM actionfinance.company_membership WHERE company_id = '9c2e0a10-4f11-4b8a-9c2e-0a104f11000c' AND role = 'OPERATOR' AND status = 'ACTIVE';
SELECT 'flyway=' || string_agg(version, ',' ORDER BY installed_rank) FROM actionfinance.flyway_schema_history;
