package br.com.banco.spider.config;

import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import br.com.banco.spider.operational.health.OperationalHealthQueryService;
import br.com.banco.spider.operational.health.ProvisionalHealthDefinitionLoader;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(OperationalHealthProperties.class)
public class OperationalHealthConfig {

  public OperationalHealthConfig(
      OperationalHealthProperties health, OperationalTelemetryProperties telemetry) {
    validate(health, telemetry);
  }

  static void validate(
      OperationalHealthProperties health, OperationalTelemetryProperties telemetry) {
    if (health.isEnabled() && !telemetry.isEnabled()) {
      throw new IllegalStateException(
          "spider.operational-health.enabled=true requires spider.telemetry.enabled=true");
    }
    if (health.getDefaultWindow() == null
        || health.getMaxWindow() == null
        || health.getAllowedWindows() == null
        || !health.getAllowedWindows().contains(health.getDefaultWindow())) {
      throw new IllegalStateException(
          "spider.operational-health.default-window must be in allowed-windows");
    }
    if (health.getDefaultWindow().compareTo(health.getMaxWindow()) > 0) {
      throw new IllegalStateException(
          "spider.operational-health.max-window must cover default-window");
    }
    if (health.getMinimumSampleSize() <= 0 || health.getMaxResults() <= 0) {
      throw new IllegalStateException(
          "spider.operational-health sample and result bounds must be positive");
    }
    if (health.getAllowedWindows().stream()
        .anyMatch(
            window ->
                window == null
                    || window.isZero()
                    || window.isNegative()
                    || window.compareTo(health.getMaxWindow()) > 0)) {
      throw new IllegalStateException("spider.operational-health.allowed-windows is invalid");
    }
    if (health.getAgedWaitThreshold() == null
        || health.getAgedWaitThreshold().compareTo(Duration.ZERO) <= 0) {
      throw new IllegalStateException(
          "spider.operational-health.aged-wait-threshold must be positive");
    }
  }

  @Bean
  @ConditionalOnProperty(name = "spider.operational-health.enabled", havingValue = "true")
  ProvisionalHealthDefinitionLoader provisionalHealthDefinitionLoader(ObjectMapper mapper) {
    return new ProvisionalHealthDefinitionLoader(mapper);
  }

  @Bean
  @ConditionalOnProperty(name = "spider.operational-health.enabled", havingValue = "true")
  OperationalHealthQueryService operationalHealthQueryService(
      OperationalHealthProperties properties,
      SpiderClock clock,
      ProvisionalHealthDefinitionLoader loader,
      ObjectProvider<ExecutionControlStorePort> control,
      ObjectProvider<ExecutionWaitStorePort> waits,
      ObjectProvider<CallbackOutboxStorePort> callbacks,
      ObjectProvider<OperationalEventStorePort> events) {
    return new OperationalHealthQueryService(
        properties, clock, loader, control, waits, callbacks, events);
  }
}
