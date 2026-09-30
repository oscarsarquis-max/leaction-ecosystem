package br.com.actionfinance;

import br.com.actionfinance.support.PostgresFoundationContainer;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@Testcontainers
class FoundationPersistenceIT {

    @Container
    static final PostgreSQLContainer<?> POSTGRES = PostgresFoundationContainer.create();

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "actionfinance_runtime");
        registry.add("spring.datasource.password", () -> "runtime-test");
        registry.add("spring.flyway.user", () -> "actionfinance_migrator");
        registry.add("spring.flyway.password", () -> "migrator-test");
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("actionfinance.demo-auth.enabled", () -> "false");
    }

    @Autowired
    DataSource dataSource;

    @Autowired
    Flyway flyway;

    @Test
    void appliesFoundationMigrationOnceAndKeepsChecksum() throws Exception {
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        Integer appliedBefore = jdbc.queryForObject(
                "select count(*) from actionfinance.flyway_schema_history where success", Integer.class);
        Integer checksumBefore = jdbc.queryForObject(
                "select checksum from actionfinance.flyway_schema_history where version = '1'", Integer.class);
        assertThat(appliedBefore).isGreaterThanOrEqualTo(3);
        assertThat(checksumBefore).isEqualTo(1_488_219_560);

        var migrate = flyway.migrate();
        assertThat(migrate.migrationsExecuted).isZero();

        Integer appliedAfter = jdbc.queryForObject(
                "select count(*) from actionfinance.flyway_schema_history where success", Integer.class);
        Integer checksumAfter = jdbc.queryForObject(
                "select checksum from actionfinance.flyway_schema_history where version = '1'", Integer.class);
        assertThat(appliedAfter).isEqualTo(appliedBefore);
        assertThat(checksumAfter).isEqualTo(checksumBefore);

        try (Connection connection =
                        DriverManager.getConnection(
                                POSTGRES.getJdbcUrl(), "actionfinance_runtime", "runtime-test");
                Statement statement = connection.createStatement()) {
            assertThatThrownBy(() -> statement.execute("create table actionfinance.forbidden(id int)"))
                    .isInstanceOf(Exception.class);
            try (ResultSet roles =
                    statement.executeQuery(
                            "select rolsuper, rolcreatedb, rolcreaterole from pg_roles where rolname = 'actionfinance_runtime'")) {
                assertThat(roles.next()).isTrue();
                assertThat(roles.getBoolean("rolsuper")).isFalse();
                assertThat(roles.getBoolean("rolcreatedb")).isFalse();
                assertThat(roles.getBoolean("rolcreaterole")).isFalse();
            }
        }
    }
}
