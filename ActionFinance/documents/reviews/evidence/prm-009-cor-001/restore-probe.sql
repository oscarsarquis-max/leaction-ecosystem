SELECT 'flyway='||string_agg(version, ',' ORDER BY installed_rank) FROM actionfinance.flyway_schema_history WHERE success
UNION ALL SELECT 'tenant='||count(*)::text FROM actionfinance.tenant
UNION ALL SELECT 'company='||count(*)::text FROM actionfinance.company
UNION ALL SELECT 'run='||count(*)::text FROM actionfinance.pay_receipt_sync_run
UNION ALL SELECT 'txn='||count(*)::text FROM actionfinance.pay_receipt_transaction
UNION ALL SELECT 'rev='||count(*)::text FROM actionfinance.pay_receipt_transaction_revision
UNION ALL SELECT 'chk='||count(*)::text FROM actionfinance.pay_receipt_checkpoint
UNION ALL SELECT 'fk_ok='||(
  SELECT count(*)::text FROM actionfinance.pay_receipt_sync_run r
  JOIN actionfinance.company c ON c.tenant_id = r.tenant_id AND c.id = r.company_id
)
UNION ALL SELECT 'orphans='||(
  SELECT count(*)::text FROM actionfinance.pay_receipt_sync_run r
  LEFT JOIN actionfinance.company c ON c.tenant_id = r.tenant_id AND c.id = r.company_id
  WHERE c.id IS NULL
);
SELECT relname||':'||privilege_type
FROM information_schema.role_table_grants g
JOIN pg_class c ON c.relname = g.table_name
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = g.table_schema
WHERE g.grantee = 'actionfinance_runtime'
  AND g.table_schema = 'actionfinance'
  AND g.table_name LIKE 'pay_receipt%'
ORDER BY 1;
