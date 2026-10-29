package br.com.banco.spider.application.security;

import br.com.banco.spider.execution.signal.ConfiguredExternalSignalAuthorization;
import br.com.banco.spider.execution.signal.ExternalSignalAuthorizationPort;
import java.util.Set;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;

/**
 * Substitui os adapters DenyAll do ingress canônico somente com profile {@code sandbox}. Não ativa
 * {@code local-demo}.
 */
@Configuration
@Profile("sandbox")
public class SandboxCanonicalSecurityConfig {

  @Bean
  @Primary
  CanonicalIngressAuthenticationPort sandboxCanonicalIngressAuthentication() {
    return new SandboxCanonicalIngressAuthenticationAdapter();
  }

  @Bean
  @Primary
  CanonicalExecutionAuthorizationPort sandboxCanonicalExecutionAuthorization() {
    return new SandboxCanonicalExecutionAuthorizationAdapter();
  }

  @Bean
  @Primary
  ExternalSignalIngressAuthenticationPort sandboxSignalIngressAuthentication() {
    return new SandboxExternalSignalIngressAuthenticationAdapter();
  }

  @Bean
  @Primary
  ExternalSignalAuthorizationPort sandboxSignalAuthorization() {
    return new ConfiguredExternalSignalAuthorization(
        Set.of(SandboxCanonicalCredentials.PRINCIPAL_REF, "principal:test-signal@1.0"),
        Set.of(SandboxCanonicalCredentials.SIGNAL_SOURCE_REF, "source:test-signal@1.0"));
  }
}
