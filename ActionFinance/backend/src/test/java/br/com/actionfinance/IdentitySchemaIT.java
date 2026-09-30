package br.com.actionfinance;

import br.com.actionfinance.support.PostgresFoundationContainer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@Testcontainers
class IdentitySchemaIT {

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
    JdbcTemplate jdbc;

    @Test
    void keepsV1ChecksumAndAddsIdentityAndSessionTables() throws Exception {
        Integer checksum =
                jdbc.queryForObject(
                        "select checksum from actionfinance.flyway_schema_history where version = '1'", Integer.class);
        assertThat(checksum).isEqualTo(1_488_219_560);
        Integer latest =
                jdbc.queryForObject(
                        "select max(installed_rank) from actionfinance.flyway_schema_history where success",
                        Integer.class);
        assertThat(latest).isGreaterThanOrEqualTo(7);
        assertThat(jdbc.queryForObject("select count(*) from actionfinance.app_user", Integer.class)).isZero();

        try (Connection connection =
                        DriverManager.getConnection(POSTGRES.getJdbcUrl(), "actionfinance_runtime", "runtime-test");
                Statement statement = connection.createStatement()) {
            assertThatThrownBy(
                            () -> statement.execute("delete from actionfinance.access_admin_audit where false"))
                    .isInstanceOf(Exception.class);
            statement.execute("delete from actionfinance.\"spring_session\" where false");
        }
    }
}
