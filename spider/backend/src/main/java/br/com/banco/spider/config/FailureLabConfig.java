package br.com.banco.spider.config;

import br.com.banco.spider.execution.engine.CanonicalExecutionEngine;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.execution.retry.ConfiguredRetryPolicyCatalog;
import br.com.banco.spider.execution.retry.RetryPolicyCatalogPort;
import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteCatalogPort;
import br.com.banco.spider.execution.signal.ExecutionResumeService;
import br.com.banco.spider.execution.signal.ExternalSignalIngressUseCase;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ConfiguredWaitPolicyCatalog;
import br.com.banco.spider.execution.wait.WaitPolicyCatalogPort;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import br.com.banco.spider.operational.failurelab.FailureLabCatalogLoader;
import br.com.banco.spider.operational.failurelab.FailureLabEvidenceService;
import br.com.banco.spider.operational.failurelab.FailureLabObservationVerifier;
import br.com.banco.spider.operational.failurelab.FailureLabOrchestrator;
import br.com.banco.spider.operational.failurelab.FailureLabQueryService;
import br.com.banco.spider.operational.failurelab.FailureLabRouteSupport;
import br.com.banco.spider.operational.failurelab.FailureLabRunStorePort;
import br.com.banco.spider.operational.failurelab.FailureLabSubmitSupport;
import br.com.banco.spider.operational.failurelab.InMemoryFailureLabRunStore;
import br.com.banco.spider.operational.health.OperationalHealthQueryService;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.core.env.Environment;

/**
 * Wiring do Failure Lab. Todo o conjunto só existe quando {@code spider.failure-lab.enabled=true};
 * a Engine canônica permanece sem qualquer condicional de laboratório.
 */
@Configuration
@EnableConfigurationProperties(FailureLabProperties.class)
public class FailureLabConfig {

  private static final Logger log = LoggerFactory.getLogger(FailureLabConfig.class);
  private static final Duration MAX_RUN_DURATION_UPPER_BOUND = Duration.ofMinutes(15);
  private static final String ENABLED = "spider.failure-lab.enabled";

  public FailureLabConfig(FailureLabProperties properties, Environment environment) {
    validate(properties, environment);
  }

  static void validate(FailureLabProperties properties, Environment environment) {
    if (properties.getHttp().isEnabled() && !properties.isEnabled()) {
      throw new IllegalStateException(
          "spider.failure-lab.http.enabled=true requer spider.failure-lab.enabled=true");
    }
    if (properties.getLocalDemo().isEnabled() && !properties.isEnabled()) {
      throw new IllegalStateException(
          "spider.failure-lab.local-demo.enabled=true requer spider.failure-lab.enabled=true");
    }
    if (properties.getMaxConcurrentRuns() < 1) {
      throw new IllegalStateException("spider.failure-lab.max-concurrent-runs deve ser >= 1");
    }
    if (properties.getMaxExecutionsPerRun() < 1 || properties.getMaxExecutionsPerRun() > 10) {
      throw new IllegalStateException(
          "spider.failure-lab.max-executions-per-run deve estar entre 1 e 10");
    }
    Duration maxRunDuration = properties.getMaxRunDuration();
    if (maxRunDuration == null
        || maxRunDuration.isZero()
        || maxRunDuration.isNegative()
        || maxRunDuration.compareTo(MAX_RUN_DURATION_UPPER_BOUND) > 0) {
      throw new IllegalStateException(
          "spider.failure-lab.max-run-duration deve ser positiva e no máximo PT15M");
    }
    if (properties.isEnabled()
        && environment != null
        && !environment.getProperty("spider.adapter.mock.enabled", Boolean.class, Boolean.TRUE)) {
      log.warn(
          "event=failure_lab_precondition_warning reasonCode=MOCK_ADAPTER_DISABLED "
              + "detail=cenarios_do_laboratorio_dependem_do_adapter_mock");
    }
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  FailureLabCatalogLoader failureLabCatalogLoader(ObjectMapper mapper) {
    return new FailureLabCatalogLoader(mapper);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  FailureLabRunStorePort failureLabRunStore() {
    return new InMemoryFailureLabRunStore();
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  FailureLabObservationVerifier failureLabObservationVerifier(
      SpiderClock clock,
      ObjectProvider<ExecutionControlStorePort> controls,
      ObjectProvider<StepAttemptStorePort> attempts,
      ObjectProvider<ExecutionWaitStorePort> waits,
      ObjectProvider<OperationalEventStorePort> events,
      ObjectProvider<CallbackOutboxStorePort> callbacks,
      ObjectProvider<OperationalHealthQueryService> health) {
    return new FailureLabObservationVerifier(
        clock, controls, attempts, waits, events, callbacks, health);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  FailureLabEvidenceService failureLabEvidenceService(SpiderClock clock, IdentifierGenerator ids) {
    return new FailureLabEvidenceService(clock, ids);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  FailureLabSubmitSupport failureLabSubmitSupport(
      CanonicalExecutionEngine engine,
      IdentifierGenerator ids,
      SpiderClock clock,
      ObjectMapper mapper) {
    return new FailureLabSubmitSupport(engine, ids, clock, mapper);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  FailureLabOrchestrator failureLabOrchestrator(
      FailureLabProperties properties,
      FailureLabCatalogLoader catalog,
      FailureLabRunStorePort store,
      FailureLabSubmitSupport submitSupport,
      FailureLabObservationVerifier verifier,
      FailureLabEvidenceService evidenceService,
      SpiderClock clock,
      IdentifierGenerator ids,
      ObjectProvider<ExecutionWaitStorePort> waits,
      ObjectProvider<ExecutionResumeService> resume,
      ObjectProvider<ExternalSignalIngressUseCase> signalIngress) {
    return new FailureLabOrchestrator(
        properties,
        catalog,
        store,
        submitSupport,
        verifier,
        evidenceService,
        clock,
        ids,
        waits,
        resume,
        signalIngress);
  }

  @Bean
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  FailureLabQueryService failureLabQueryService(
      FailureLabCatalogLoader catalog, FailureLabRunStorePort store) {
    return new FailureLabQueryService(catalog, store);
  }

  /**
   * Catálogos publicados do laboratório. São {@code @Primary} porque o wiring padrão registra
   * catálogos vazios; sem isso a resolução de rota do cenário não encontraria destino.
   */
  @Bean
  @Primary
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  RouteCatalogPort failureLabRouteCatalog() {
    return new InMemoryRouteCatalog(FailureLabRouteSupport.routes());
  }

  @Bean
  @Primary
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  RetryPolicyCatalogPort failureLabRetryPolicyCatalog() {
    return new ConfiguredRetryPolicyCatalog(FailureLabRouteSupport.retryPolicies());
  }

  @Bean
  @Primary
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  WaitPolicyCatalogPort failureLabWaitPolicyCatalog() {
    return new ConfiguredWaitPolicyCatalog(FailureLabRouteSupport.waitPolicies());
  }
}
