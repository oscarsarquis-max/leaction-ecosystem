package br.com.banco.spider.config;

import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteCatalogPort;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionPlanStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionRecoveryQuery;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionResultStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionStepStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionTransitionStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionWaitStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryInboxStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryIdempotencyStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryStepAttemptStore;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionPlanStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionRecoveryQueryPort;
import br.com.banco.spider.execution.persistence.port.ExecutionResultStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionTransitionStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.IdempotencyStorePort;
import br.com.banco.spider.execution.persistence.port.InboxStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import java.util.List;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class CanonicalEngineConfig {

  @Bean
  @ConditionalOnMissingBean(br.com.banco.spider.execution.retry.RetryPolicyCatalogPort.class)
  br.com.banco.spider.execution.retry.RetryPolicyCatalogPort emptyRetryPolicyCatalog() {
    return new br.com.banco.spider.execution.retry.EmptyRetryPolicyCatalog();
  }

  @Bean
  @ConditionalOnMissingBean(br.com.banco.spider.execution.wait.WaitPolicyCatalogPort.class)
  br.com.banco.spider.execution.wait.WaitPolicyCatalogPort emptyWaitPolicyCatalog() {
    return new br.com.banco.spider.execution.wait.EmptyWaitPolicyCatalog();
  }

  @Bean
  @ConditionalOnMissingBean(IdentifierGenerator.class)
  IdentifierGenerator identifierGenerator() {
    return IdentifierGenerator.uuid();
  }

  @Bean
  @ConditionalOnMissingBean(SpiderClock.class)
  SpiderClock spiderClock() {
    return SpiderClock.systemUtc();
  }

  @Bean
  @ConditionalOnMissingBean(IntegrityDigestPort.class)
  IntegrityDigestPort integrityDigestPort() {
    return IntegrityDigestPort.sha256();
  }

  @Bean
  @ConditionalOnMissingBean(RouteCatalogPort.class)
  RouteCatalogPort routeCatalogPort() {
    return new InMemoryRouteCatalog(List.<RouteDefinition>of());
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  ExecutionControlStorePort executionControlStorePort() {
    return new InMemoryExecutionControlStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  ExecutionPlanStorePort executionPlanStorePort() {
    return new InMemoryExecutionPlanStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  ExecutionTransitionStorePort executionTransitionStorePort() {
    return new InMemoryExecutionTransitionStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  ExecutionResultStorePort executionResultStorePort() {
    return new InMemoryExecutionResultStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  IdempotencyStorePort idempotencyStorePort() {
    return new InMemoryIdempotencyStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  ExecutionStepStorePort executionStepStorePort() {
    return new InMemoryExecutionStepStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  StepAttemptStorePort stepAttemptStorePort() {
    return new InMemoryStepAttemptStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  ExecutionWaitStorePort executionWaitStorePort() {
    return new InMemoryExecutionWaitStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  InboxStorePort inboxStorePort() {
    return new InMemoryInboxStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  br.com.banco.spider.execution.persistence.port.ExecutionCallbackContextStorePort
      executionCallbackContextStorePort() {
    return new br.com.banco.spider.infrastructure.persistence.memory
        .InMemoryExecutionCallbackContextStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort callbackOutboxStorePort() {
    return new br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackOutboxStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  br.com.banco.spider.execution.persistence.port.CallbackDeliveryAttemptStorePort
      callbackDeliveryAttemptStorePort() {
    return new br.com.banco.spider.infrastructure.persistence.memory
        .InMemoryCallbackDeliveryAttemptStore();
  }

  @Bean
  @ConditionalOnMissingBean(br.com.banco.spider.execution.callback.CallbackDefinitionCatalogPort.class)
  br.com.banco.spider.execution.callback.CallbackDefinitionCatalogPort
      emptyCallbackDefinitionCatalog() {
    return new br.com.banco.spider.execution.callback.ConfiguredCallbackDefinitionCatalog(
        java.util.List.of());
  }

  @Bean
  @ConditionalOnMissingBean(
      br.com.banco.spider.execution.callback.CallbackDeliveryPolicyCatalogPort.class)
  br.com.banco.spider.execution.callback.CallbackDeliveryPolicyCatalogPort
      emptyCallbackDeliveryPolicyCatalog() {
    return new br.com.banco.spider.execution.callback.ConfiguredCallbackDeliveryPolicyCatalog(
        java.util.List.of());
  }

  @Bean
  @ConditionalOnMissingBean(br.com.banco.spider.execution.callback.CallbackBindingResolverPort.class)
  br.com.banco.spider.execution.callback.CallbackBindingResolverPort emptyCallbackBindingResolver() {
    return new br.com.banco.spider.execution.callback.ConfiguredCallbackBindingResolver(
        java.util.Map.of());
  }

  @Bean
  @ConditionalOnMissingBean(
      br.com.banco.spider.execution.callback.CallbackReconciliationPolicyCatalogPort.class)
  br.com.banco.spider.execution.callback.CallbackReconciliationPolicyCatalogPort
      emptyCallbackReconciliationPolicyCatalog() {
    return new br.com.banco.spider.execution.callback.ConfiguredCallbackReconciliationPolicyCatalog(
        java.util.List.of());
  }

  @Bean
  @ConditionalOnMissingBean(
      br.com.banco.spider.execution.callback.CallbackStatusQueryBindingResolver.class)
  br.com.banco.spider.execution.callback.CallbackStatusQueryBindingResolver
      emptyCallbackStatusQueryBindingResolver() {
    return new br.com.banco.spider.execution.callback.ConfiguredCallbackStatusQueryBindingResolver(
        java.util.Map.of());
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort
      callbackReconciliationStorePort() {
    return new br.com.banco.spider.infrastructure.persistence.memory
        .InMemoryCallbackReconciliationStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  br.com.banco.spider.execution.persistence.port.CallbackReconciliationAttemptStorePort
      callbackReconciliationAttemptStorePort() {
    return new br.com.banco.spider.infrastructure.persistence.memory
        .InMemoryCallbackReconciliationAttemptStore();
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  ExecutionRecoveryQueryPort executionRecoveryQueryPort(
      ExecutionControlStorePort controlStore, ExecutionPlanStorePort planStore) {
    return new InMemoryExecutionRecoveryQuery(controlStore, planStore);
  }
}
