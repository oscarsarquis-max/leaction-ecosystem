package br.com.banco.spider.config;

import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.config.SatelliteContractProperties.SatelliteEntry;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Profile;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

/**
 * Falha o startup do profile production quando a configuração está ausente ou cruzada com sandbox.
 */
@Component
@Profile("production")
@EnableConfigurationProperties(SatelliteContractProperties.class)
public class ProductionProfileGuard implements ApplicationRunner {

  static final String PRODUCTION_COMPANY = "624023a4-57e3-415c-b7d0-925ca1acd3b7";
  static final String SANDBOX_COMPANY = "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c";

  private final Environment environment;
  private final SatelliteContractProperties satellite;

  public ProductionProfileGuard(Environment environment, SatelliteContractProperties satellite) {
    this.environment = environment;
    this.satellite = satellite;
  }

  @Override
  public void run(ApplicationArguments args) {
    List<String> errors = validate(environment, satellite);
    if (!errors.isEmpty()) {
      throw new IllegalStateException(
          "production profile rejected: " + String.join("; ", errors));
    }
  }

  static List<String> validate(Environment environment, SatelliteContractProperties satellite) {
    List<String> errors = new ArrayList<>();
    String plane = environment.getProperty("spider.plane", "combined");
    boolean runtime = "runtime".equals(plane) || "combined".equals(plane);
    boolean observationPlane = "projector".equals(plane) || "query".equals(plane) || "combined".equals(plane);
    String canonical = environment.getProperty("spider.canonical.persistence.mode", "");
    String monitor = environment.getProperty("spider.monitor.persistence.mode", "");
    if (runtime && !"jpa".equals(canonical)) {
      errors.add("canonical persistence must be jpa");
    }
    if (observationPlane && !"jpa".equals(monitor)) {
      errors.add("monitor persistence must be jpa");
    }
    if ("runtime".equals(plane)
        && !"outbox".equals(environment.getProperty("spider.observation.dispatch", ""))) {
      errors.add("runtime must persist observation facts in the operational outbox");
    }
    if (runtime) {
      requireHttpsPostgres(environment, "SPIDER_CANONICAL_JDBC_URL", "spring.datasource.url", errors);
    }
    if (observationPlane) {
      requireHttpsPostgres(environment, "SPIDER_MONITOR_JDBC_URL", "spider.monitor.persistence.jdbc.url", errors);
    }
    if (!runtime) {
      return errors;
    }
    requirePresent(environment, "SPIDER_JWT_SECRET", "spider.jwt.secret", errors);
    if (environment.getProperty("spider.adapter.mock.enabled", Boolean.class, Boolean.FALSE)) {
      errors.add("mock adapter must stay disabled");
    }
    if (satellite == null || satellite.getProviders() == null) {
      errors.add("satellite providers are required");
      return errors;
    }
    ProviderEntry pay = satellite.getProviders().get("actionhub-pay");
    if (pay == null) {
      errors.add("actionhub-pay provider is required");
      return errors;
    }
    if (!"ACTIVE".equals(pay.getStatus())) {
      errors.add("actionhub-pay status must be ACTIVE");
    }
    String baseUrl = pay.getBaseUrl() == null ? "" : pay.getBaseUrl().toLowerCase(Locale.ROOT);
    if (!baseUrl.startsWith("https://") || baseUrl.contains("sandbox") || baseUrl.contains("spider.actionhub")) {
      errors.add("actionhub-pay base URL must be the production edge");
    }
    if (!StringUtils.hasText(pay.getSecret())) {
      errors.add("actionhub-pay secret is required");
    }
    if (pay.getCapabilities() == null
        || pay.getCapabilities().size() != 1
        || !"LIST_PAYMENT_TRANSACTIONS".equals(pay.getCapabilities().get(0))) {
      errors.add("only LIST_PAYMENT_TRANSACTIONS is allowed");
    }
    SatelliteEntry actionFinance =
        satellite.getRegistry() == null ? null : satellite.getRegistry().get("actionfinance");
    if (actionFinance == null) {
      errors.add("actionfinance satellite is required");
      return errors;
    }
    if (!StringUtils.hasText(actionFinance.getSecret())) {
      errors.add("actionfinance application secret is required");
    }
    if (actionFinance.getAllowedObjectives() == null
        || actionFinance.getAllowedObjectives().size() != 1
        || !"LIST_EXTERNAL_PAYMENTS".equals(actionFinance.getAllowedObjectives().get(0))) {
      errors.add("only LIST_EXTERNAL_PAYMENTS is allowed");
    }
    List<String> companies =
        actionFinance.getAllowedAttributes() == null
            ? List.of()
            : actionFinance.getAllowedAttributes().getOrDefault("companyId", List.of());
    if (!Set.copyOf(companies).equals(Set.of(PRODUCTION_COMPANY)) || companies.contains(SANDBOX_COMPANY)) {
      errors.add("company scope must be the production company only");
    }
    return errors;
  }

  private static void requirePresent(
      Environment environment, String envName, String property, List<String> errors) {
    if (!StringUtils.hasText(environment.getProperty(property))) {
      errors.add(envName + " is required");
    }
  }

  private static void requireHttpsPostgres(
      Environment environment, String envName, String property, List<String> errors) {
    String url = environment.getProperty(property, "");
    String normalized = url.toLowerCase(Locale.ROOT);
    if (!normalized.startsWith("jdbc:postgresql://")
        || normalized.contains("localhost")
        || normalized.contains("127.0.0.1")
        || normalized.contains("sandbox")) {
      errors.add(envName + " must be the production PostgreSQL URL");
    }
  }
}
