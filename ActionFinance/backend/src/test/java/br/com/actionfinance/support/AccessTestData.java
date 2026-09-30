package br.com.actionfinance.support;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.UUID;

public final class AccessTestData {

    private AccessTestData() {}

    public static void seedCompanies(JdbcTemplate jdbc) {
        Instant now = Instant.parse("2026-09-29T12:00:00Z");
        Timestamp ts = Timestamp.from(now);
        jdbc.update(
                """
                insert into actionfinance.tenant (id, code, name, active, created_at, updated_at, version)
                values (?,?,?,true,?,?,1)
                on conflict (id) do nothing
                """,
                DemoPrincipalCatalog.TENANT_A,
                "TENANT-A",
                "Organização A",
                ts,
                ts);
        insertCompany(jdbc, DemoPrincipalCatalog.COMPANY_A, DemoPrincipalCatalog.TENANT_A, "EMP-A", "Empresa Alfa", ts);
        insertCompany(jdbc, DemoPrincipalCatalog.COMPANY_C, DemoPrincipalCatalog.TENANT_A, "EMP-C", "Empresa Gama", ts);
        jdbc.update(
                """
                insert into actionfinance.tenant (id, code, name, active, created_at, updated_at, version)
                values (?,?,?,true,?,?,1)
                on conflict (id) do nothing
                """,
                DemoPrincipalCatalog.TENANT_B,
                "TENANT-B",
                "Organização B",
                ts,
                ts);
        insertCompany(jdbc, DemoPrincipalCatalog.COMPANY_B, DemoPrincipalCatalog.TENANT_B, "EMP-B", "Empresa Beta", ts);
    }

    private static void insertCompany(
            JdbcTemplate jdbc, UUID id, UUID tenantId, String code, String name, Timestamp ts) {
        jdbc.update(
                """
                insert into actionfinance.company (
                    id, tenant_id, code, name, active, is_demo, business_timezone, created_at, updated_at, version)
                values (?,?,?,?,true,false,'America/Sao_Paulo',?,?,1)
                on conflict (id) do nothing
                """,
                id,
                tenantId,
                code,
                name,
                ts,
                ts);
    }
}
