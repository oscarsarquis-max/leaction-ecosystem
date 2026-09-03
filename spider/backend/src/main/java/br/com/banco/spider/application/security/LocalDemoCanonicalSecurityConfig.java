package br.com.banco.spider.application.security;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;

/**
 * Substitui os adapters DenyAll do ingress canônico somente com profile {@code local-demo} e flag
 * explícita. Fora desse recorte os beans DenyAll de {@code CanonicalSecurityDefaultsConfig}
 * permanecem.
 */
@Configuration
@Profile("local-demo")
@ConditionalOnProperty(name = "spider.console.local-demo.enabled", havingValue = "true")
public class LocalDemoCanonicalSecurityConfig {

  @Bean
  @Primary
  CanonicalIngressAuthenticationPort localDemoCanonicalIngressAuthentication() {
    return new LocalDemoCanonicalIngressAuthenticationAdapter();
  }

  @Bean
  @Primary
  CanonicalExecutionAuthorizationPort localDemoCanonicalExecutionAuthorization() {
    return new LocalDemoCanonicalExecutionAuthorizationAdapter();
  }

  @Bean
  @Primary
  ExternalSignalIngressAuthenticationPort localDemoSignalIngressAuthentication() {
    return new LocalDemoExternalSignalIngressAuthenticationAdapter();
  }
}
