package br.com.banco.spider.config;

import br.com.banco.spider.execution.callback.CallbackOutboxProcessor;
import br.com.banco.spider.execution.callback.CallbackProcessingRecoveryService;
import br.com.banco.spider.execution.callback.CallbackReconciliationProcessor;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.InboxStorePort;
import br.com.banco.spider.execution.signal.ExternalSignalApplicationProcessor;
import br.com.banco.spider.execution.signal.ExternalSignalApplicationRecoveryService;
import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeRetentionService;
import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.WaitExpiryProcessor;
import br.com.banco.spider.infrastructure.persistence.jpa.JpaDurableScheduleStoreAdapter;
import br.com.banco.spider.infrastructure.persistence.jpa.JpaWorkerInstanceStoreAdapter;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.RuntimeScheduleJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.RuntimeWorkerInstanceJpaRepository;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryDurableScheduleStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryWorkerInstanceStore;
import br.com.banco.spider.operational.capacity.BulkheadService;
import br.com.banco.spider.operational.capacity.CapacityAdmissionService;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.workers.DurableScheduleStorePort;
import br.com.banco.spider.operational.workers.FailureLabWorkerHarness;
import br.com.banco.spider.operational.workers.RequestWorkerDrainUseCase;
import br.com.banco.spider.operational.workers.WorkerBacklogQueryService;
import br.com.banco.spider.operational.workers.WorkerInstanceStorePort;
import br.com.banco.spider.operational.workers.WorkerRuntimeCatalog;
import br.com.banco.spider.operational.workers.WorkerRuntimeCoordinator;
import br.com.banco.spider.operational.workers.WorkerRuntimeQueryService;
import br.com.banco.spider.operational.workers.WorkerRuntimeTelemetry;
import br.com.banco.spider.operational.workers.WorkerScheduleRunner;
import br.com.banco.spider.operational.workers.WorkerTypeHandler;
import br.com.banco.spider.operational.workers.handlers.CallbackDeliveryWorkerHandler;
import br.com.banco.spider.operational.workers.handlers.CallbackReconciliationWorkerHandler;
import br.com.banco.spider.operational.workers.handlers.CallbackRecoveryWorkerHandler;
import br.com.banco.spider.operational.workers.handlers.ProtectedEnvelopeMaintenanceWorkerHandler;
import br.com.banco.spider.operational.workers.handlers.SignalApplicationRecoveryWorkerHandler;
import br.com.banco.spider.operational.workers.handlers.SignalApplicationWorkerHandler;
import br.com.banco.spider.operational.workers.handlers.WaitExpiryWorkerHandler;
import java.time.Duration;
import java.util.List;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Wiring do runtime de workers duráveis. Todo o conjunto só existe quando
 * {@code spider.worker-runtime.enabled=true}; a Engine canônica e os processadores continuam sem
 * qualquer condicional de runtime.
 */
@Configuration
@EnableConfigurationProperties(WorkerRuntimeProperties.class)
public class WorkerRuntimeConfig {

  static final String ENABLED = "spider.worker-runtime.enabled";
  static final String PERSISTENCE_MODE = "spider.canonical.persistence.mode";
  private static final Duration MAX_TICK_INTERVAL = Duration.ofSeconds(60);

  public WorkerRuntimeConfig(WorkerRuntimeProperties properties) {
    validate(properties);
  }

  static void validate(WorkerRuntimeProperties properties) {
    if (properties.getHttp().isEnabled() && !properties.isEnabled()) {
      throw new IllegalStateException(
          "spider.worker-runtime.http.enabled=true requer spider.worker-runtime.enabled=true");
    }
    if (properties.getLocalDemo().isEnabled() && !properties.isEnabled()) {
      throw new IllegalStateException(
          "spider.worker-runtime.local-demo.enabled=true requer spider.worker-runtime.enabled=true");
    }
    requirePositive("heartbeat-interval", properties.getHeartbeatInterval());
    requirePositive("stale-after", properties.getStaleAfter());
    requirePositive("tick-interval", properties.getTickInterval());
    requirePositive("default-lease-duration", properties.getDefaultLeaseDuration());
    requirePositive("default-execution-timeout", properties.getDefaultExecutionTimeout());
    requirePositive("drain-timeout", properties.getDrainTimeout());
    if (properties.getHeartbeatInterval().compareTo(properties.getStaleAfter()) >= 0) {
      throw new IllegalStateException(
          "spider.worker-runtime.heartbeat-interval deve ser menor que stale-after");
    }
    if (properties.getDefaultLeaseDuration().compareTo(properties.getHeartbeatInterval()) <= 0) {
      throw new IllegalStateException(
          "spider.worker-runtime.default-lease-duration deve ser maior que heartbeat-interval");
    }
    if (properties.getTickInterval().compareTo(MAX_TICK_INTERVAL) > 0) {
      throw new IllegalStateException(
          "spider.worker-runtime.tick-interval deve ser no máximo PT60S");
    }
    if (properties.getTickInterval().compareTo(properties.getStaleAfter()) >= 0) {
      throw new IllegalStateException(
          "spider.worker-runtime.tick-interval deve ser menor que stale-after");
    }
    if (properties.getDefaultBatchSize() < 1
        || properties.getDefaultBatchSize() > WorkerRuntimeCatalog.MAX_BATCH_SIZE) {
      throw new IllegalStateException(
          "spider.worker-runtime.default-batch-size deve estar entre 1 e "
              + WorkerRuntimeCatalog.MAX_BATCH_SIZE);
    }
    if (properties.getMaxConcurrency() < 1 || properties.getMaxConcurrency() > 16) {
      throw new IllegalStateException(
          "spider.worker-runtime.max-concurrency deve estar entre 1 e 16");
    }
    if (properties.getMaxAttempts() < 1 || properties.getMaxAttempts() > 10) {
      throw new IllegalStateException("spider.worker-runtime.max-attempts deve estar entre 1 e 10");
    }
    if (properties.getDefaultExecutionTimeout().compareTo(properties.getDefaultLeaseDuration())
        > 0) {
      throw new IllegalStateException(
          "spider.worker-runtime.default-execution-timeout não pode exceder default-lease-duration");
    }
  }

  private static void requirePositive(String name, Duration value) {
    if (value == null || value.isZero() || value.isNegative()) {
      throw new IllegalStateException("spider.worker-runtime." + name + " deve ser positiva");
    }
  }

  @Configuration(proxyBeanMethods = false)
  @ConditionalOnProperty(name = ENABLED, havingValue = "true")
  static class Runtime {

    // Os condicionais de armazenamento ficam nos próprios métodos: uma classe @Configuration
    // aninhada seria descoberta pelo scan por conta própria e escaparia do flag do runtime.

    /** Armazenamento em memória do runtime — modo padrão de persistência canônica. */
    @Bean
    @ConditionalOnProperty(name = PERSISTENCE_MODE, havingValue = "memory", matchIfMissing = true)
    WorkerInstanceStorePort memoryWorkerInstanceStorePort() {
      return new InMemoryWorkerInstanceStore();
    }

    @Bean
    @ConditionalOnProperty(name = PERSISTENCE_MODE, havingValue = "memory", matchIfMissing = true)
    DurableScheduleStorePort memoryDurableScheduleStorePort() {
      return new InMemoryDurableScheduleStore();
    }

    /** Armazenamento durável em Postgres — mesma semântica de CAS, exclusão mútua no banco. */
    @Bean
    @ConditionalOnProperty(name = PERSISTENCE_MODE, havingValue = "jpa")
    WorkerInstanceStorePort jpaWorkerInstanceStorePort(RuntimeWorkerInstanceJpaRepository repo) {
      return new JpaWorkerInstanceStoreAdapter(repo);
    }

    @Bean
    @ConditionalOnProperty(name = PERSISTENCE_MODE, havingValue = "jpa")
    DurableScheduleStorePort jpaDurableScheduleStorePort(RuntimeScheduleJpaRepository repo) {
      return new JpaDurableScheduleStoreAdapter(repo);
    }

    @Bean
    WorkerRuntimeCatalog workerRuntimeCatalog(WorkerRuntimeProperties properties) {
      return new WorkerRuntimeCatalog(
          properties.getDefaultBatchSize(),
          properties.getDefaultLeaseDuration(),
          properties.getDefaultExecutionTimeout(),
          properties.getMaxAttempts());
    }

    @Bean
    WorkerRuntimeTelemetry workerRuntimeTelemetry(
        ObjectProvider<OperationalEventPublisher> publishers) {
      return new WorkerRuntimeTelemetry(publishers);
    }

    @Bean
    WorkerTypeHandler signalApplicationWorkerHandler(ExternalSignalApplicationProcessor processor) {
      return new SignalApplicationWorkerHandler(processor);
    }

    @Bean
    WorkerTypeHandler waitExpiryWorkerHandler(WaitExpiryProcessor processor) {
      return new WaitExpiryWorkerHandler(processor);
    }

    @Bean
    WorkerTypeHandler callbackDeliveryWorkerHandler(CallbackOutboxProcessor processor) {
      return new CallbackDeliveryWorkerHandler(processor);
    }

    @Bean
    WorkerTypeHandler callbackReconciliationWorkerHandler(
        CallbackReconciliationProcessor processor) {
      return new CallbackReconciliationWorkerHandler(processor);
    }

    @Bean
    WorkerTypeHandler callbackRecoveryWorkerHandler(CallbackProcessingRecoveryService service) {
      return new CallbackRecoveryWorkerHandler(service);
    }

    @Bean
    WorkerTypeHandler signalApplicationRecoveryWorkerHandler(
        ExternalSignalApplicationRecoveryService service) {
      return new SignalApplicationRecoveryWorkerHandler(service);
    }

    @Bean
    WorkerTypeHandler protectedEnvelopeMaintenanceWorkerHandler(
        ObjectProvider<ProtectedSignalEnvelopeRetentionService> retention) {
      return new ProtectedEnvelopeMaintenanceWorkerHandler(retention);
    }

    /**
     * A admissão de capacidade entra por {@code ObjectProvider}: com {@code spider.capacity.enabled}
     * desligado nenhum bean existe e o ciclo é idêntico ao de 019.
     */
    @Bean
    WorkerScheduleRunner workerScheduleRunner(
        WorkerRuntimeCatalog catalog,
        DurableScheduleStorePort scheduleStore,
        WorkerInstanceStorePort instanceStore,
        WorkerRuntimeTelemetry telemetry,
        SpiderClock clock,
        ObjectProvider<CapacityAdmissionService> admission,
        ObjectProvider<BulkheadService> bulkheads) {
      return new WorkerScheduleRunner(
          catalog, scheduleStore, instanceStore, telemetry, clock, admission, bulkheads);
    }

    @Bean
    WorkerBacklogQueryService workerBacklogQueryService(
        WorkerRuntimeCatalog catalog,
        SpiderClock clock,
        ObjectProvider<InboxStorePort> inbox,
        ObjectProvider<ExecutionWaitStorePort> waits,
        ObjectProvider<CallbackOutboxStorePort> outbox,
        ObjectProvider<CallbackReconciliationStorePort> reconciliations,
        ObjectProvider<ProtectedSignalEnvelopeStorePort> protectedEnvelopes) {
      return new WorkerBacklogQueryService(
          catalog, clock, inbox, waits, outbox, reconciliations, protectedEnvelopes);
    }

    @Bean
    WorkerRuntimeQueryService workerRuntimeQueryService(
        WorkerRuntimeProperties properties,
        WorkerInstanceStorePort instanceStore,
        DurableScheduleStorePort scheduleStore,
        WorkerBacklogQueryService backlogService,
        SpiderClock clock) {
      return new WorkerRuntimeQueryService(
          properties, instanceStore, scheduleStore, backlogService, clock);
    }

    @Bean
    RequestWorkerDrainUseCase requestWorkerDrainUseCase(
        WorkerInstanceStorePort instanceStore,
        WorkerRuntimeCatalog catalog,
        WorkerRuntimeTelemetry telemetry,
        SpiderClock clock) {
      return new RequestWorkerDrainUseCase(instanceStore, catalog, telemetry, clock);
    }

    /** Harness do laboratório de falhas — só existe quando os dois recursos estão habilitados. */
    @Bean
    @ConditionalOnProperty(name = "spider.failure-lab.enabled", havingValue = "true")
    FailureLabWorkerHarness failureLabWorkerHarness(
        DurableScheduleStorePort scheduleStore,
        WorkerInstanceStorePort instanceStore,
        WorkerBacklogQueryService backlogService,
        RequestWorkerDrainUseCase drainUseCase,
        SpiderClock clock) {
      return new FailureLabWorkerHarness(
          scheduleStore, instanceStore, backlogService, drainUseCase, clock);
    }

    @Bean
    WorkerRuntimeCoordinator workerRuntimeCoordinator(
        WorkerRuntimeProperties properties,
        WorkerRuntimeCatalog catalog,
        DurableScheduleStorePort scheduleStore,
        WorkerInstanceStorePort instanceStore,
        WorkerScheduleRunner runner,
        WorkerRuntimeTelemetry telemetry,
        SpiderClock clock,
        List<WorkerTypeHandler> handlers) {
      return new WorkerRuntimeCoordinator(
          properties, catalog, scheduleStore, instanceStore, runner, telemetry, clock, handlers);
    }
  }
}
