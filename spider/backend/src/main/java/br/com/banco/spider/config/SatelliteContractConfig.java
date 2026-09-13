package br.com.banco.spider.config;

import br.com.banco.spider.demo.segsense.SegSenseDemoDecisionService;
import br.com.banco.spider.integration.inbound.http.satellite.SatelliteApplicationAuth;
import br.com.banco.spider.integration.outbound.provider.HttpProviderCapabilityAdapter;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.satellite.application.SatelliteInteractionService;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
@Profile("local-demo")
@ConditionalOnProperty(name = "spider.satellite.enabled", havingValue = "true")
@EnableConfigurationProperties({SatelliteContractProperties.class, SegSenseDemoProperties.class})
public class SatelliteContractConfig {

  @Bean
  SatelliteRegistry satelliteRegistry(SatelliteContractProperties properties) {
    return new SatelliteRegistry(properties);
  }

  @Bean
  SatelliteApplicationAuth satelliteApplicationAuth(SatelliteRegistry registry) {
    return new SatelliteApplicationAuth(registry);
  }

  @Bean
  ProviderCapabilityPort providerCapabilityPort(WebClient.Builder builder, SatelliteRegistry registry) {
    return new HttpProviderCapabilityAdapter(builder, registry);
  }

  @Bean
  SatelliteInteractionService satelliteInteractionService(
      SatelliteRegistry registry, ProviderCapabilityPort providers, OperationalEventPublisher events) {
    return new SatelliteInteractionService(registry, providers, events);
  }

  @Bean
  SegSenseDemoDecisionService segSenseDemoDecisionService(SatelliteInteractionService satellite) {
    return new SegSenseDemoDecisionService(satellite);
  }
}
