package br.com.banco.spider.config;

import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryOperationalEventStore;
import br.com.banco.spider.operational.events.NoOpOperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import br.com.banco.spider.operational.events.SafeOperationalEventPublisher;
import br.com.banco.spider.operational.readmodel.OperationalRedactionService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(OperationalTelemetryProperties.class)
public class OperationalTelemetryConfig {

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  OperationalEventStorePort inMemoryOperationalEventStore() {
    return new InMemoryOperationalEventStore();
  }

  @Bean
  @ConditionalOnProperty(name = "spider.telemetry.enabled", havingValue = "true")
  OperationalEventPublisher safeOperationalEventPublisher(
      IdentifierGenerator ids,
      SpiderClock clock,
      OperationalEventStorePort store,
      OperationalRedactionService redaction) {
    return new SafeOperationalEventPublisher(ids, clock, store, redaction);
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.telemetry.enabled",
      havingValue = "false",
      matchIfMissing = true)
  OperationalEventPublisher noOpOperationalEventPublisher() {
    return new NoOpOperationalEventPublisher();
  }
}
