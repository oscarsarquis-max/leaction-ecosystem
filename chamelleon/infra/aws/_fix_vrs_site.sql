INSERT INTO operational_sites (id, tenant_id, name, location, industry_type, manager_id, satellite_site_id, is_active)
SELECT gen_random_uuid(), '6a1b4bf1-d85b-4248-bbb9-452df146854c'::uuid, 'Obra Alphaville Eusebio, O1, 17', 'Eusebio', 'Construcao', '8f612875-d390-4cf5-9b06-4f03163f38fb'::uuid, 'c335f3b2-a636-489c-92c0-a63ec710a1a2', true
WHERE NOT EXISTS (
  SELECT 1 FROM operational_sites
  WHERE tenant_id = '6a1b4bf1-d85b-4248-bbb9-452df146854c'
    AND satellite_site_id = 'c335f3b2-a636-489c-92c0-a63ec710a1a2'
);

UPDATE tenant_users tu
SET operational_site_id = os.id
FROM operational_sites os
WHERE tu.tenant_id = '6a1b4bf1-d85b-4248-bbb9-452df146854c'
  AND tu.user_id = '8f612875-d390-4cf5-9b06-4f03163f38fb'
  AND os.satellite_site_id = 'c335f3b2-a636-489c-92c0-a63ec710a1a2';

SELECT id, name, satellite_site_id FROM operational_sites
WHERE tenant_id = '6a1b4bf1-d85b-4248-bbb9-452df146854c';
