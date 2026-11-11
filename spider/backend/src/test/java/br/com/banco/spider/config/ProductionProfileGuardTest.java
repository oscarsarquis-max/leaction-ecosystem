package br.com.banco.spider.config;

import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.config.SatelliteContractProperties.SatelliteEntry;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.StandardEnvironment;

class ProductionProfileGuardTest {

  @Test
  void acceptsTheProductionContract() {
    assertTrue(ProductionProfileGuard.validate(environment(true), satellite(true)).isEmpty());
  }

  @Test
  void productionHealthGroupDoesNotRequireTheProjector() throws Exception {
    String yml =
        java.nio.file.Files.readString(
            java.nio.file.Path.of("src/main/resources/application-production.yml"));
    int monitor = yml.indexOf("monitor:");
    int include = yml.indexOf("include:", monitor);
    String line = yml.substring(include, yml.indexOf('\n', include));
    assertTrue(!line.contains("projectionLag"));
  }

  @Test
  void rejectsSandboxUrlMemoryAndTestDouble() {
    List<String> errors = ProductionProfileGuard.validate(environment(false), satellite(false));
    assertTrue(errors.stream().anyMatch(item -> item.contains("canonical")));
    assertTrue(errors.stream().anyMatch(item -> item.contains("PostgreSQL")));
    assertTrue(errors.stream().anyMatch(item -> item.contains("ACTIVE") || item.contains("base URL")));
  }

  private static StandardEnvironment environment(boolean valid) {
    StandardEnvironment environment = new StandardEnvironment();
    environment
        .getPropertySources()
        .addFirst(
            new MapPropertySource(
                "test",
                Map.of(
                    "spider.canonical.persistence.mode",
                    valid ? "jpa" : "memory",
                    "spider.monitor.persistence.mode",
                    valid ? "jpa" : "memory",
                    "spider.monitor.persistence.jdbc.url",
                    valid
                        ? "jdbc:postgresql://spider-prod.example:5432/spider_orchestrator?sslmode=require"
                        : "jdbc:postgresql://localhost:5432/spider_orchestrator",
                    "spring.datasource.url",
                    valid
                        ? "jdbc:postgresql://spider-prod.example:5432/spider_orchestrator?sslmode=require"
                        : "jdbc:postgresql://localhost:5432/spider_orchestrator",
                    "spider.jwt.secret",
                    "test-jwt",
                    "spider.adapter.mock.enabled",
                    "false")));
    return environment;
  }

  private static SatelliteContractProperties satellite(boolean valid) {
    SatelliteContractProperties properties = new SatelliteContractProperties();
    ProviderEntry pay = new ProviderEntry();
    pay.setStatus(valid ? "ACTIVE" : "TEST_DOUBLE");
    pay.setBaseUrl(valid ? "https://api.actionhub.com.br" : "https://sandbox.example");
    pay.setSecret(valid ? "pay-secret" : "");
    pay.setCapabilities(List.of("LIST_PAYMENT_TRANSACTIONS"));
    properties.setProviders(Map.of("actionhub-pay", pay));
    SatelliteEntry actionFinance = new SatelliteEntry();
    actionFinance.setSecret("af-secret");
    actionFinance.setAllowedObjectives(List.of("LIST_EXTERNAL_PAYMENTS"));
    actionFinance.setAllowedAttributes(
        Map.of("companyId", List.of(ProductionProfileGuard.PRODUCTION_COMPANY)));
    properties.setRegistry(Map.of("actionfinance", actionFinance));
    return properties;
  }
}
