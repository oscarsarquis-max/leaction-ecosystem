package br.com.banco.spider.application.security;

import br.com.banco.spider.execution.signal.ConfiguredExternalSignalAuthorization;
import br.com.banco.spider.execution.signal.ExternalSignalAuthorizationPort;
import java.util.Set;
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

  /**
   * O default deny-by-default só autoriza {@code principal:test-signal@1.0}. Sem este bean o
   * segundo passo de WAIT_SIGNAL_RESUME autentica e depois cai em SIGNAL_UNAUTHORIZED.
   */
  @Bean
  @Primary
  ExternalSignalAuthorizationPort localDemoSignalAuthorization() {
    return new ConfiguredExternalSignalAuthorization(
        Set.of(LocalDemoCanonicalCredentials.PRINCIPAL_REF, "principal:test-signal@1.0"),
        Set.of(
            LocalDemoCanonicalCredentials.SIGNAL_SOURCE_REF, "source:test-signal@1.0"));
  }
}
