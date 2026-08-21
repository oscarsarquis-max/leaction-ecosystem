package br.com.banco.spider.application.console;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import reactor.core.publisher.Mono;

/**
 * Autenticação permissiva apenas sob profile {@code local-demo} + flag explícita. Ausente em runtime
 * normal.
 */
@Configuration
@Profile("local-demo")
@ConditionalOnProperty(name = "spider.console.local-demo.enabled", havingValue = "true")
public class LocalDemoOperationalConsoleSecurityConfig {

  @Bean
  @Primary
  OperationalConsoleAuthenticationPort localDemoConsoleAuthentication() {
    return credentialRef ->
        Mono.just(
            new OperationalConsoleSecurityContext(
                credentialRef == null || credentialRef.isBlank() ? "local-demo" : credentialRef,
                "LOCAL_DEMO",
                true));
  }

  @Bean
  @Primary
  OperationalConsoleAuthorizationPort localDemoConsoleAuthorization() {
    return (ctx, action) -> Mono.just(ctx.authenticated());
  }
}
