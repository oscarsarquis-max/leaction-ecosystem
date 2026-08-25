package br.com.banco.spider.config;

import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.capacity.BulkheadService;
import br.com.banco.spider.operational.capacity.CapacityAdmissionService;
import br.com.banco.spider.operational.capacity.CapacityDecisionStore;
import br.com.banco.spider.operational.capacity.CapacityPolicyCatalog;
import br.com.banco.spider.operational.capacity.CapacityPressureService;
import br.com.banco.spider.operational.capacity.CapacityQueryService;
import br.com.banco.spider.operational.capacity.CapacityTelemetry;
import br.com.banco.spider.operational.capacity.CircuitBreakerService;
import br.com.banco.spider.operational.capacity.FailureLabCapacityHarness;
import br.com.banco.spider.operational.capacity.QuotaService;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.workers.DurableScheduleStorePort;
import br.com.banco.spider.operational.workers.WorkerBacklogQueryService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Wiring do governo de capacidade. Todo o conjunto só existe quando {@code
 * spider.capacity.enabled=true}; com o flag desligado o runtime de workers é byte a byte o de 019,
 * porque o runner só consulta a admissão por {@code ObjectProvider}.
 */
@Configuration
@EnableConfigurationProperties(CapacityProperties.class)
public class CapacityConfig {

  static final String ENABLED = "spider.capacity.enabled";

  public CapacityConfig(CapacityProperties properties) {
    validate(properties);
  }

  static void validate(CapacityProperties properties) {
    if (properties.getHttp().isEnabled() && !properties.isEnabled()) {
      throw new IllegalStateException(
          "spider.capacity.http.enabled=true requer spider.capacity.enabled=true");
    }
    if (properties.getLocalDemo().isEnabled() && !properties.isEnabled()) {
      throw new IllegalStateException(
          "spider.capacity.local-demo.enabled=true requer spider.capacity.enabled=true");
    }
    if (properties.getEnforcement().isEnabled() && !properties.isEnabled()) {
      throw new IllegalStateException(
          "spider.capacity.enforcement.enabled=true requer spider.capacity.enabled=true");
    }
    if (properties.getDecisionLogSize() < 1
        || properties.getDecisionLogSize() > CapacityDecisionStore.MAX_SIZE) {
      throw new IllegalStateException(
          "spider.capacity.decision-log-size deve estar entre 1 e " + CapacityDecisionStore.MAX_SIZE);
    }
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  CapacityPolicyCatalog capacityPolicyCatalog(ObjectMapper mapper) {
    return new CapacityPolicyCatalog(mapper);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  CapacityTelemetry capacityTelemetry(ObjectProvider<OperationalEventPublisher> publishers) {
    return new CapacityTelemetry(publishers);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  CapacityDecisionStore capacityDecisionStore(CapacityProperties properties) {
    return new CapacityDecisionStore(properties.getDecisionLogSize());
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  BulkheadService bulkheadService(SpiderClock clock) {
    return new BulkheadService(clock);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  CircuitBreakerService circuitBreakerService(SpiderClock clock, CapacityTelemetry telemetry) {
    return new CircuitBreakerService(clock, telemetry);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  QuotaService quotaService(SpiderClock clock) {
    return new QuotaService(clock);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  CapacityAdmissionService capacityAdmissionService(
      CapacityProperties properties,
      CapacityPolicyCatalog catalog,
      BulkheadService bulkheads,
      CircuitBreakerService circuits,
      QuotaService quotas,
      CapacityDecisionStore decisions,
      CapacityTelemetry telemetry,
      SpiderClock clock,
      IdentifierGenerator ids,
      ObjectProvider<WorkerBacklogQueryService> backlogs) {
    return new CapacityAdmissionService(
        properties,
        catalog,
        bulkheads,
        circuits,
        quotas,
        decisions,
        telemetry,
        clock,
        ids,
        backlogs);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  CapacityPressureService capacityPressureService(
      CapacityPolicyCatalog catalog,
      BulkheadService bulkheads,
      CircuitBreakerService circuits,
      QuotaService quotas,
      SpiderClock clock,
      ObjectProvider<WorkerBacklogQueryService> backlogs) {
    return new CapacityPressureService(catalog, bulkheads, circuits, quotas, clock, backlogs);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  CapacityQueryService capacityQueryService(
      CapacityProperties properties,
      CapacityPolicyCatalog catalog,
      CapacityPressureService pressure,
      BulkheadService bulkheads,
      CircuitBreakerService circuits,
      CapacityDecisionStore decisions,
      SpiderClock clock) {
    return new CapacityQueryService(
        properties, catalog, pressure, bulkheads, circuits, decisions, clock);
  }

  /** Harness do laboratório de falhas — só existe quando os dois recursos estão habilitados. */
  @Bean
  @ConditionalOnProperty(
      name = {ENABLED, "spider.failure-lab.enabled"},
      havingValue = "true")
  FailureLabCapacityHarness failureLabCapacityHarness(
      CapacityAdmissionService admission,
      BulkheadService bulkheads,
      CircuitBreakerService circuits,
      QuotaService quotas,
      SpiderClock clock,
      ObjectProvider<DurableScheduleStorePort> scheduleStore) {
    return new FailureLabCapacityHarness(
        admission, bulkheads, circuits, quotas, clock, scheduleStore);
  }
}
