package br.com.banco.spider.application.console;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import reactor.core.publisher.Mono;

/**
 * Console operacional do profile {@code production}. A credencial é distinta de {@code
 * sandbox-operator} e de {@code local-demo-console}.
 */
@Configuration
@Profile("production")
public class ProductionOperationalConsoleSecurityConfig {

  @Bean
  @Primary
  OperationalConsoleAuthenticationPort productionConsoleAuthentication(
      @Value("${spider.console.credential-ref:production-operator}") String credentialRef) {
    String expected = credentialRef == null ? "" : credentialRef.trim();
    return presented ->
        Mono.just(
            !expected.isBlank() && expected.equals(presented)
                ? new OperationalConsoleSecurityContext("owner:production", "PRODUCTION", true)
                : OperationalConsoleSecurityContext.anonymous());
  }

  @Bean
  @Primary
  OperationalConsoleAuthorizationPort productionConsoleAuthorization() {
    return (ctx, action) -> Mono.just(ctx.authenticated());
  }
}
