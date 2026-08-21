package br.com.banco.spider.application.canonical;

import br.com.banco.spider.application.security.AuthorizationDecision;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

@Configuration
public class CallbackOpsAuthorizationDefaultsConfig {

  @Bean
  @ConditionalOnMissingBean(CallbackOpsAuthorizationPort.class)
  CallbackOpsAuthorizationPort denyAllCallbackOpsAuthorization() {
    return (operation, actor) -> Mono.just(AuthorizationDecision.DENY);
  }
}
