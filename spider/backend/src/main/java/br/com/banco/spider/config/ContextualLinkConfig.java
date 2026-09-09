package br.com.banco.spider.config;

import br.com.banco.spider.context.application.ContextDecisionStore;
import br.com.banco.spider.context.application.ContextIntelligenceService;
import br.com.banco.spider.context.application.ContextInterpretationService;
import br.com.banco.spider.contextuallink.application.ContextualLinkGatewayService;
import br.com.banco.spider.contextuallink.application.ContextualLinkStore;
import br.com.banco.spider.contextuallink.application.InMemoryContextualLinkStore;
import br.com.banco.spider.contextuallink.application.PageAcquisitionPort;
import br.com.banco.spider.contextuallink.application.SpiderBankUnderstandService;
import br.com.banco.spider.contextuallink.application.WebClientPageAcquisition;
import br.com.banco.spider.contextuallink.domain.AcquisitionUrlGuard;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
@Profile("local-demo")
@ConditionalOnProperty(name = "spider.demo.contextual-link.enabled", havingValue = "true")
@EnableConfigurationProperties(ContextualLinkProperties.class)
public class ContextualLinkConfig {

  @Bean
  ContextualLinkStore contextualLinkStore() {
    return new InMemoryContextualLinkStore();
  }

  @Bean
  AcquisitionUrlGuard acquisitionUrlGuard(ContextualLinkProperties properties) {
    return new AcquisitionUrlGuard(
        properties.getAcquisition().getAllowedOrigins(),
        properties.getAcquisition().getAllowedPathPrefixes());
  }

  @Bean
  PageAcquisitionPort pageAcquisitionPort(
      WebClient.Builder builder, AcquisitionUrlGuard guard, ContextualLinkProperties properties) {
    return new WebClientPageAcquisition(
        builder,
        guard,
        properties.getAcquisition().getMaxBytes(),
        properties.getAcquisition().getTimeout());
  }

  @Bean
  ContextualLinkGatewayService contextualLinkGatewayService(
      IdentifierGenerator ids,
      SpiderClock clock,
      ContextualLinkStore store,
      PageAcquisitionPort pages,
      AcquisitionUrlGuard guard,
      OperationalEventPublisher events,
      ContextualLinkProperties properties) {
    return new ContextualLinkGatewayService(ids, clock, store, pages, guard, events, properties);
  }

  @Bean
  @ConditionalOnProperty(name = "spider.context.enabled", havingValue = "true")
  SpiderBankUnderstandService spiderBankUnderstandService(
      ContextualLinkGatewayService gateway,
      ContextInterpretationService interpretation,
      ContextIntelligenceService intelligence,
      ContextDecisionStore decisions,
      OperationalEventPublisher events) {
    return new SpiderBankUnderstandService(
        gateway, interpretation, intelligence, decisions, events);
  }
}
