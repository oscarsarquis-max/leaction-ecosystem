package br.com.actionfinance.infrastructure.health;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

@Component("flywaySchema")
public class FlywaySchemaHealthIndicator implements HealthIndicator {

    private final DataSource dataSource;

    public FlywaySchemaHealthIndicator(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public Health health() {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement =
                        connection.prepareStatement(
                                "select count(*) from actionfinance.flyway_schema_history where success and version = '1'")) {
            try (ResultSet resultSet = statement.executeQuery()) {
                if (resultSet.next() && resultSet.getInt(1) == 1) {
                    return Health.up().build();
                }
            }
            return Health.down().build();
        } catch (Exception exception) {
            return Health.down().build();
        }
    }
}
