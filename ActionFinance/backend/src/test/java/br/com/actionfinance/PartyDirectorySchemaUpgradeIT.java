package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.LocalDemoSeed;
import br.com.actionfinance.support.PostgresFoundationContainer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Ensaio de upgrade de schema num Testcontainer descartável.
 * Não prova cópia restaurada do RDS público: PartyDirectoryIT também cria o próprio container.
 * Ensaio com dump restaurado exige JDBC explícito isolado ({@code rehearse-isolated-upgrade-012.ps1}).
 */
@SpringBootTest
@ActiveProfiles("local-demo")
@Testcontainers
class PartyDirectorySchemaUpgradeIT {

    @Container
    static final PostgreSQLContainer<?> POSTGRES = PostgresFoundationContainer.create();

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "actionfinance_runtime");
        registry.add("spring.datasource.password", () -> "runtime-test");
        registry.add("spring.flyway.user", () -> "actionfinance_migrator");
        registry.add("spring.flyway.password", () -> "migrator-test");
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("actionfinance.demo-auth.enabled", () -> "false");
    }

    @Autowired
    JdbcTemplate jdbc;

    @Test
    void appliesV17AndKeepsTitleLinksAndCompositeIntegrity() throws Exception {
        Integer latestRank = jdbc.queryForObject(
                "select max(installed_rank) from actionfinance.flyway_schema_history where success", Integer.class);
        String latestVersion = jdbc.queryForObject(
                """
                select version from actionfinance.flyway_schema_history
                 where success
                 order by installed_rank desc
                 limit 1
                """,
                String.class);
        assertThat(latestRank).isGreaterThanOrEqualTo(19);
        assertThat(latestVersion).isEqualTo("19");
        assertThat(jdbc.queryForObject(
                        "select checksum from actionfinance.flyway_schema_history where version = '13'", Integer.class))
                .isEqualTo(728_072_343);
        assertThat(jdbc.queryForObject(
                        "select count(*) from actionfinance.flyway_schema_history where version in ('14','15','16','17','18','19') and success",
                        Integer.class))
                .isEqualTo(6);

        assertThat(jdbc.queryForObject(
                        """
                        select is_nullable from information_schema.columns
                         where table_schema = 'actionfinance'
                           and table_name = 'counterparty_external_identity'
                           and column_name = 'connection_key'
                        """,
                        String.class))
                .isEqualTo("NO");

        String addressFkCols = jdbc.queryForObject(
                """
                select string_agg(kcu.column_name, ',' order by kcu.ordinal_position)
                  from information_schema.referential_constraints rc
                  join information_schema.key_column_usage kcu
                    on rc.constraint_name = kcu.constraint_name
                   and rc.constraint_schema = kcu.constraint_schema
                 where rc.constraint_schema = 'actionfinance'
                   and rc.constraint_name = 'counterparty_address_unit_fk'
                """,
                String.class);
        assertThat(addressFkCols).isEqualTo("tenant_id,company_id,counterparty_id,unit_id");

        Integer titles = jdbc.queryForObject(
                """
                select count(*) from actionfinance.financial_title
                 where counterparty_id = ?
                """,
                Integer.class,
                LocalDemoSeed.CP_PADARIA_FORNECEDOR);
        assertThat(titles).isGreaterThan(0);

        UUID unitId = UUID.fromString("aaaaaaaa-0120-4111-8111-000000000001");
        UUID addressId = UUID.fromString("aaaaaaaa-0120-4111-8111-000000000002");
        UUID extA = UUID.fromString("aaaaaaaa-0120-4111-8111-000000000003");
        UUID extB = UUID.fromString("aaaaaaaa-0120-4111-8111-000000000004");
        try (Connection connection =
                        DriverManager.getConnection(POSTGRES.getJdbcUrl(), "actionfinance_runtime", "runtime-test");
                Statement statement = connection.createStatement()) {
            statement.execute(
                    """
                    insert into actionfinance.counterparty_unit (
                        id, tenant_id, company_id, counterparty_id, name, unit_kind, is_primary, active,
                        version, created_at, updated_at, created_by, updated_by)
                    values ('%s', '%s', '%s', '%s', 'Unidade do cliente', 'STORE', true, true,
                            1, now(), now(), '%s', '%s')
                    """
                            .formatted(
                                    unitId,
                                    DemoPrincipalCatalog.TENANT_A,
                                    DemoPrincipalCatalog.COMPANY_A,
                                    LocalDemoSeed.CP_PADARIA_CLIENTE,
                                    DemoPrincipalCatalog.OPERATOR_A,
                                    DemoPrincipalCatalog.OPERATOR_A));
            assertThatThrownBy(
                            () ->
                                    statement.execute(
                                            """
                                            insert into actionfinance.counterparty_address (
                                                id, tenant_id, company_id, counterparty_id, unit_id, country,
                                                usage, incomplete, active, version, created_at, updated_at,
                                                created_by, updated_by)
                                            values ('%s', '%s', '%s', '%s', '%s', 'BR',
                                                    'MAIN', true, true, 1, now(), now(), '%s', '%s')
                                            """
                                                    .formatted(
                                                            addressId,
                                                            DemoPrincipalCatalog.TENANT_A,
                                                            DemoPrincipalCatalog.COMPANY_A,
                                                            LocalDemoSeed.CP_PADARIA_FORNECEDOR,
                                                            unitId,
                                                            DemoPrincipalCatalog.OPERATOR_A,
                                                            DemoPrincipalCatalog.OPERATOR_A)))
                    .isInstanceOf(Exception.class);

            statement.execute(
                    """
                    insert into actionfinance.counterparty_external_identity (
                        id, tenant_id, company_id, counterparty_id, origin_system, connection_key,
                        external_id, created_at, created_by)
                    values ('%s', '%s', '%s', '%s', 'FILE', '',
                            'EXT-SCHEMA-012', now(), '%s')
                    """
                            .formatted(
                                    extA,
                                    DemoPrincipalCatalog.TENANT_A,
                                    DemoPrincipalCatalog.COMPANY_A,
                                    LocalDemoSeed.CP_PADARIA_CLIENTE,
                                    DemoPrincipalCatalog.OPERATOR_A));
            assertThatThrownBy(
                            () ->
                                    statement.execute(
                                            """
                                            insert into actionfinance.counterparty_external_identity (
                                                id, tenant_id, company_id, counterparty_id, origin_system, connection_key,
                                                external_id, created_at, created_by)
                                            values ('%s', '%s', '%s', '%s', 'FILE', '',
                                                    'EXT-SCHEMA-012', now(), '%s')
                                            """
                                                    .formatted(
                                                            extB,
                                                            DemoPrincipalCatalog.TENANT_A,
                                                            DemoPrincipalCatalog.COMPANY_A,
                                                            LocalDemoSeed.CP_PADARIA_FORNECEDOR,
                                                            DemoPrincipalCatalog.OPERATOR_A)))
                    .isInstanceOf(Exception.class);

            statement.execute("select 1 from actionfinance.counterparty_document_claim limit 1");
        }
    }
}
