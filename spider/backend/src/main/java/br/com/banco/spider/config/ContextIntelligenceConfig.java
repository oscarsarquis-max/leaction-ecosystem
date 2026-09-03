package br.com.banco.spider.config;

import br.com.banco.spider.application.canonical.SubmitCanonicalExecutionUseCase;
import br.com.banco.spider.context.application.ContextDecisionStore;
import br.com.banco.spider.context.application.ContextIntelligenceService;
import br.com.banco.spider.context.application.InMemoryContextDecisionStore;
import br.com.banco.spider.context.domain.BusinessIntentCatalog;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.DeterministicIntentRouter;
import br.com.banco.spider.context.domain.StaticBusinessIntentCatalog;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(ContextIntelligenceProperties.class)
@ConditionalOnProperty(name = "spider.context.enabled", havingValue = "true")
public class ContextIntelligenceConfig {

  @Bean
  BusinessIntentCatalog businessIntentCatalog() {
    return new StaticBusinessIntentCatalog();
  }

  @Bean
  ContextPolicyGuard contextPolicyGuard(BusinessIntentCatalog catalog) {
    return new ContextPolicyGuard(catalog);
  }

  @Bean
  DeterministicIntentRouter deterministicIntentRouter(BusinessIntentCatalog catalog) {
    return new DeterministicIntentRouter(catalog);
  }

  @Bean
  ContextDecisionStore contextDecisionStore() {
    return new InMemoryContextDecisionStore();
  }

  @Bean
  ContextIntelligenceService contextIntelligenceService(
      BusinessIntentCatalog catalog,
      ContextPolicyGuard guard,
      DeterministicIntentRouter router,
      ContextDecisionStore store,
      SubmitCanonicalExecutionUseCase canonicalSubmit,
      OperationalEventPublisher events,
      IdentifierGenerator ids,
      SpiderClock clock,
      ObjectMapper mapper) {
    return new ContextIntelligenceService(
        catalog, guard, router, store, canonicalSubmit, events, ids, clock, mapper);
  }
}
