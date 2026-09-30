package br.com.actionfinance.support;

import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

public final class PostgresFoundationContainer {

    public static final String IMAGE = "postgres:17.6";

    private PostgresFoundationContainer() {}

    public static PostgreSQLContainer<?> create() {
        return new PostgreSQLContainer<>(DockerImageName.parse(IMAGE))
                .withDatabaseName("actionfinance")
                .withUsername("actionfinance_bootstrap")
                .withPassword("bootstrap-test")
                .withInitScript("test-init.sql");
    }
}
