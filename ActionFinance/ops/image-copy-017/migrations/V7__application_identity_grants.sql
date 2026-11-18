GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.app_user TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.external_identity TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.company_membership TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.access_admin_audit TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE actionfinance.SPRING_SESSION TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE actionfinance.SPRING_SESSION_ATTRIBUTES TO actionfinance_runtime;

REVOKE DELETE ON TABLE actionfinance.app_user FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.external_identity FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.company_membership FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.access_admin_audit FROM actionfinance_runtime;
