package br.com.banco.spider.config;

import br.com.banco.spider.execution.persistence.port.CallbackDeliveryAttemptStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationAttemptStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackDeliveryAttemptStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackOutboxStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackReconciliationAttemptStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackReconciliationStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionStepStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryStepAttemptStore;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Ports canônicos que ainda não têm adaptador JPA. O Monitor e os stores JPA existentes continuam
 * no PostgreSQL. Estes gaps não gravam efeito financeiro.
 */
@Configuration
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class CanonicalJpaGapConfig {

  @Bean
  @ConditionalOnMissingBean(ExecutionStepStorePort.class)
  ExecutionStepStorePort executionStepStorePort() {
    return new InMemoryExecutionStepStore();
  }

  @Bean
  @ConditionalOnMissingBean(StepAttemptStorePort.class)
  StepAttemptStorePort stepAttemptStorePort() {
    return new InMemoryStepAttemptStore();
  }

  @Bean
  @ConditionalOnMissingBean(CallbackOutboxStorePort.class)
  CallbackOutboxStorePort callbackOutboxStorePort() {
    return new InMemoryCallbackOutboxStore();
  }

  @Bean
  @ConditionalOnMissingBean(CallbackDeliveryAttemptStorePort.class)
  CallbackDeliveryAttemptStorePort callbackDeliveryAttemptStorePort() {
    return new InMemoryCallbackDeliveryAttemptStore();
  }

  @Bean
  @ConditionalOnMissingBean(CallbackReconciliationStorePort.class)
  CallbackReconciliationStorePort callbackReconciliationStorePort() {
    return new InMemoryCallbackReconciliationStore();
  }

  @Bean
  @ConditionalOnMissingBean(CallbackReconciliationAttemptStorePort.class)
  CallbackReconciliationAttemptStorePort callbackReconciliationAttemptStorePort() {
    return new InMemoryCallbackReconciliationAttemptStore();
  }
}
