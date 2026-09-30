package br.com.banco.spider.application.console;

import br.com.banco.spider.application.security.SandboxCanonicalCredentials;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import reactor.core.publisher.Mono;

/**
 * Autenticação do console operacional no profile {@code sandbox}. Credencial distinta de {@code
 * local-demo-console}. Sem header ou valor estranho permanece anônimo.
 */
@Configuration
@Profile("sandbox")
public class SandboxOperationalConsoleSecurityConfig {

  @Bean
  @Primary
  OperationalConsoleAuthenticationPort sandboxConsoleAuthentication() {
    return credentialRef ->
        Mono.just(
            SandboxCanonicalCredentials.credentialAllowed(credentialRef)
                ? new OperationalConsoleSecurityContext(
                    SandboxCanonicalCredentials.PRINCIPAL_REF, "SANDBOX", true)
                : OperationalConsoleSecurityContext.anonymous());
  }

  @Bean
  @Primary
  OperationalConsoleAuthorizationPort sandboxConsoleAuthorization() {
    return (ctx, action) -> Mono.just(ctx.authenticated());
  }
}
