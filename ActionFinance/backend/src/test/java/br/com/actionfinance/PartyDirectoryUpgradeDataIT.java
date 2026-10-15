package br.com.actionfinance;

import br.com.actionfinance.support.PostgresFoundationContainer;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.FlywayException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Ensaio com dados inseridos antes da correção de integridade.
 * Não é cópia restaurada do RDS público.
 */
@Testcontainers
class PartyDirectoryUpgradeDataIT {

    @Container
    static final PostgreSQLContainer<?> POSTGRES = PostgresFoundationContainer.create();

    private static final UUID TENANT = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0131");
    private static final UUID COMPANY = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0132");
    private static final UUID ACTOR = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0133");
    private static final UUID PERSON_ONLY = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0141");
    private static final UUID UNIT_OWN = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0142");
    private static final UUID MIRROR = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0143");
    private static final UUID INACTIVE = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0144");
    private static final UUID UNIT_OWN_ID = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0151");
    private static final UUID MIRROR_UNIT = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0152");
    private static final UUID INACTIVE_UNIT = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0153");
    private static final UUID TITLE = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0161");
    private static final UUID CATEGORY = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0162");
    private static final UUID LEGACY_PARTY = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0163");

    @BeforeEach
    void resetSchema() {
        Flyway.configure()
                .dataSource(POSTGRES.getJdbcUrl(), "actionfinance_migrator", "migrator-test")
                .schemas("actionfinance")
                .defaultSchema("actionfinance")
                .locations(migrationsLocation())
                .cleanDisabled(false)
                .load()
                .clean();
    }

    @Test
    void preservesV13LinksThenAppliesDirectoryAndOldInsertStillWorks() throws Exception {
        flyway("13").migrate();
        try (Connection connection = migrator()) {
            insertTenantCompany(connection);
            insertPartyV13(connection, LEGACY_PARTY, "Fornecedor V13");
            insertCategory(connection);
            insertTitle(connection, LEGACY_PARTY);
        }
        flyway("19").migrate();
        try (Connection connection = runtime();
                PreparedStatement title = connection.prepareStatement(
                        """
                        select t.id, t.counterparty_id, t.amount_minor, c.name, c.role, c.document_pending
                          from actionfinance.financial_title t
                          join actionfinance.counterparty c
                            on c.tenant_id = t.tenant_id and c.company_id = t.company_id and c.id = t.counterparty_id
                         where t.id = ?
                        """)) {
            title.setObject(1, TITLE);
            try (ResultSet rs = title.executeQuery()) {
                assertThat(rs.next()).isTrue();
                assertThat(rs.getObject("id", UUID.class)).isEqualTo(TITLE);
                assertThat(rs.getObject("counterparty_id", UUID.class)).isEqualTo(LEGACY_PARTY);
                assertThat(rs.getLong("amount_minor")).isEqualTo(1500);
                assertThat(rs.getString("name")).isEqualTo("Fornecedor V13");
                assertThat(rs.getString("role")).isEqualTo("SUPPLIER");
                assertThat(rs.getBoolean("document_pending")).isTrue();
            }
        }
        try (Connection connection = runtime();
                PreparedStatement insert = connection.prepareStatement(
                        """
                        insert into actionfinance.counterparty (
                            id, tenant_id, company_id, code, name, role, active, version,
                            created_at, updated_at, created_by, updated_by)
                        values (?,?,?,?,?,?,?,?, now(), now(), ?, ?)
                        """)) {
            UUID leftover = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0164");
            insert.setObject(1, leftover);
            insert.setObject(2, TENANT);
            insert.setObject(3, COMPANY);
            insert.setString(4, "CTP-" + leftover);
            insert.setString(5, "Imagem anterior 013");
            insert.setString(6, "CUSTOMER");
            insert.setBoolean(7, true);
            insert.setLong(8, 1);
            insert.setObject(9, ACTOR);
            insert.setObject(10, ACTOR);
            assertThat(insert.executeUpdate()).isEqualTo(1);
        }
    }

    @Test
    void backfillsClaimsFromV15WithoutSilentOwnerChoice() throws Exception {
        flyway("15").migrate();
        try (Connection connection = migrator()) {
            insertTenantCompany(connection);
            insertPartyV15(connection, PERSON_ONLY, "Pessoa só documento", "20000000000107");
            insertPartyV15(connection, UNIT_OWN, "Pessoa unidade própria", null);
            insertPartyV15(connection, MIRROR, "Pessoa espelho", "55000000000183");
            insertPartyV15(connection, INACTIVE, "Pessoa unidade inativa", null);
            insertUnit(connection, UNIT_OWN_ID, UNIT_OWN, "Filial própria", false, true, "33000000000140");
            insertUnit(connection, MIRROR_UNIT, MIRROR, "Sede espelho", true, true, "55000000000183");
            insertUnit(connection, INACTIVE_UNIT, INACTIVE, "Inativa", true, false, "66000000000108");
        }
        flyway("19").migrate();
        assertClaim(PERSON_ONLY, "20000000000107", null, false);
        assertClaim(UNIT_OWN, "33000000000140", UNIT_OWN_ID, false);
        assertClaim(MIRROR, "55000000000183", MIRROR_UNIT, true);
        assertClaim(INACTIVE, "66000000000108", INACTIVE_UNIT, false);
    }

    @Test
    void refusesPreexistingDocumentConflictWithoutPickingOwner() throws Exception {
        flyway("15").migrate();
        UUID other = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0171");
        UUID otherUnit = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0172");
        try (Connection connection = migrator()) {
            insertTenantCompany(connection);
            insertPartyV15(connection, PERSON_ONLY, "Dono A", "77000000000116");
            insertPartyV15(connection, other, "Dono B", null);
            insertUnit(connection, otherUnit, other, "Unidade alheia", true, true, "77000000000116");
        }
        assertThatThrownBy(() -> flyway("19").migrate())
                .isInstanceOf(FlywayException.class)
                .hasMessageContaining("counterparty_document_claim conflito");
    }

    private static Flyway flyway(String target) {
        return Flyway.configure()
                .dataSource(POSTGRES.getJdbcUrl(), "actionfinance_migrator", "migrator-test")
                .schemas("actionfinance")
                .defaultSchema("actionfinance")
                .locations(migrationsLocation())
                .target(target)
                .load();
    }

    private static String migrationsLocation() {
        if (Files.isDirectory(Path.of("database", "migrations"))) {
            return "filesystem:database/migrations";
        }
        return "filesystem:../database/migrations";
    }

    private static Connection migrator() throws Exception {
        return DriverManager.getConnection(POSTGRES.getJdbcUrl(), "actionfinance_migrator", "migrator-test");
    }

    private static Connection runtime() throws Exception {
        return DriverManager.getConnection(POSTGRES.getJdbcUrl(), "actionfinance_runtime", "runtime-test");
    }

    private static void insertTenantCompany(Connection connection) throws Exception {
        try (PreparedStatement tenant = connection.prepareStatement(
                        """
                        insert into actionfinance.tenant (id, code, name, active, created_at, updated_at, version)
                        values (?, 'T013', 'Tenant 013', true, now(), now(), 1)
                        on conflict (id) do nothing
                        """);
                PreparedStatement company = connection.prepareStatement(
                        """
                        insert into actionfinance.company (
                            id, tenant_id, code, name, active, is_demo, business_timezone,
                            created_at, updated_at, version)
                        values (?, ?, 'C013', 'Empresa 013', true, false, 'America/Sao_Paulo', now(), now(), 1)
                        on conflict (id) do nothing
                        """)) {
            tenant.setObject(1, TENANT);
            tenant.executeUpdate();
            company.setObject(1, COMPANY);
            company.setObject(2, TENANT);
            company.executeUpdate();
        }
    }

    private static void insertPartyV13(Connection connection, UUID id, String name) throws Exception {
        try (PreparedStatement statement = connection.prepareStatement(
                """
                insert into actionfinance.counterparty (
                    id, tenant_id, company_id, code, name, role, active, version,
                    created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,'SUPPLIER', true, 1, now(), now(), ?, ?)
                """)) {
            statement.setObject(1, id);
            statement.setObject(2, TENANT);
            statement.setObject(3, COMPANY);
            statement.setString(4, "CTP-" + id);
            statement.setString(5, name);
            statement.setObject(6, ACTOR);
            statement.setObject(7, ACTOR);
            statement.executeUpdate();
        }
    }

    private static void insertPartyV15(Connection connection, UUID id, String name, String document) throws Exception {
        try (PreparedStatement statement = connection.prepareStatement(
                """
                insert into actionfinance.counterparty (
                    id, tenant_id, company_id, code, name, role, active, version,
                    created_at, updated_at, created_by, updated_by,
                    person_kind, document_country, document_type, document_number,
                    document_number_normalized, document_pending, origin_kind)
                values (?,?,?,?,?,'SUPPLIER', true, 1, now(), now(), ?, ?,
                        'LEGAL', ?, ?, ?, ?, ?, 'MANUAL')
                """)) {
            statement.setObject(1, id);
            statement.setObject(2, TENANT);
            statement.setObject(3, COMPANY);
            statement.setString(4, "CTP-" + id);
            statement.setString(5, name);
            statement.setObject(6, ACTOR);
            statement.setObject(7, ACTOR);
            if (document == null) {
                statement.setObject(8, null);
                statement.setObject(9, null);
                statement.setObject(10, null);
                statement.setObject(11, null);
                statement.setBoolean(12, true);
            } else {
                statement.setString(8, "BR");
                statement.setString(9, "CNPJ");
                statement.setString(10, document);
                statement.setString(11, document);
                statement.setBoolean(12, false);
            }
            statement.executeUpdate();
        }
    }

    private static void insertUnit(
            Connection connection, UUID id, UUID partyId, String name, boolean primary, boolean active, String document)
            throws Exception {
        try (PreparedStatement statement = connection.prepareStatement(
                """
                insert into actionfinance.counterparty_unit (
                    id, tenant_id, company_id, counterparty_id, name, unit_kind, is_primary, active,
                    document_country, document_type, document_number, document_number_normalized,
                    version, created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,'STORE',?,?, 'BR','CNPJ',?,?, 1, now(), now(), ?, ?)
                """)) {
            statement.setObject(1, id);
            statement.setObject(2, TENANT);
            statement.setObject(3, COMPANY);
            statement.setObject(4, partyId);
            statement.setString(5, name);
            statement.setBoolean(6, primary);
            statement.setBoolean(7, active);
            statement.setString(8, document);
            statement.setString(9, document);
            statement.setObject(10, ACTOR);
            statement.setObject(11, ACTOR);
            statement.executeUpdate();
        }
    }

    private static void insertCategory(Connection connection) throws Exception {
        try (PreparedStatement statement = connection.prepareStatement(
                """
                insert into actionfinance.financial_category (
                    id, tenant_id, company_id, code, name, direction, active, version,
                    created_at, updated_at, created_by, updated_by)
                values (?,?,?,'CAT-013','Insumos 013','PAYABLE', true, 1, now(), now(), ?, ?)
                """)) {
            statement.setObject(1, CATEGORY);
            statement.setObject(2, TENANT);
            statement.setObject(3, COMPANY);
            statement.setObject(4, ACTOR);
            statement.setObject(5, ACTOR);
            statement.executeUpdate();
        }
    }

    private static void insertTitle(Connection connection, UUID partyId) throws Exception {
        try (PreparedStatement statement = connection.prepareStatement(
                """
                insert into actionfinance.financial_title (
                    id, tenant_id, company_id, reference, direction, status, description,
                    counterparty_id, category_id, amount_minor, currency, competence_date, due_date,
                    origin_kind, version, created_at, updated_at, created_by, updated_by)
                values (?,?,?,'REF-013','PAYABLE','DRAFT','Compra 013',?,?,1500,'BRL','2026-10-01','2026-10-10',
                        'MANUAL', 1, now(), now(), ?, ?)
                """)) {
            statement.setObject(1, TITLE);
            statement.setObject(2, TENANT);
            statement.setObject(3, COMPANY);
            statement.setObject(4, partyId);
            statement.setObject(5, CATEGORY);
            statement.setObject(6, ACTOR);
            statement.setObject(7, ACTOR);
            statement.executeUpdate();
        }
    }

    private static void assertClaim(UUID partyId, String normalized, UUID unitId, boolean mirrored) throws Exception {
        try (Connection connection = runtime();
                PreparedStatement statement = connection.prepareStatement(
                        """
                        select counterparty_id, unit_id, mirrored
                          from actionfinance.counterparty_document_claim
                         where company_id = ? and document_number_normalized = ?
                        """)) {
            statement.setObject(1, COMPANY);
            statement.setString(2, normalized);
            try (ResultSet rs = statement.executeQuery()) {
                assertThat(rs.next()).as("claim for " + normalized).isTrue();
                assertThat(rs.getObject("counterparty_id", UUID.class)).isEqualTo(partyId);
                if (unitId == null) {
                    assertThat(rs.getObject("unit_id")).isNull();
                } else {
                    assertThat(rs.getObject("unit_id", UUID.class)).isEqualTo(unitId);
                }
                assertThat(rs.getBoolean("mirrored")).isEqualTo(mirrored);
                assertThat(rs.next()).isFalse();
            }
        }
    }
}
