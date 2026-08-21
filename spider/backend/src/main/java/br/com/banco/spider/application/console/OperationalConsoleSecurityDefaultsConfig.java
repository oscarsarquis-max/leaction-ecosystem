package br.com.banco.spider.application.console;

import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

@Configuration
public class OperationalConsoleSecurityDefaultsConfig {

  @Bean
  @ConditionalOnMissingBean(OperationalConsoleAuthenticationPort.class)
  OperationalConsoleAuthenticationPort denyAllOperationalConsoleAuthentication() {
    return credentialRef -> Mono.just(OperationalConsoleSecurityContext.anonymous());
  }

  @Bean
  @ConditionalOnMissingBean(OperationalConsoleAuthorizationPort.class)
  OperationalConsoleAuthorizationPort denyAllOperationalConsoleAuthorization() {
    return (ctx, action) -> Mono.just(false);
  }
}
