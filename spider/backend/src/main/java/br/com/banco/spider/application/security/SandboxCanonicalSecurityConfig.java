package br.com.banco.spider.application.security;

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
}
