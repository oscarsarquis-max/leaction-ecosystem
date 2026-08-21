package br.com.banco.spider.governance;

import br.com.banco.spider.application.security.AuthorizationDecision;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

@Configuration
public class GovernanceAuthorizationDefaultsConfig {

  @Bean
  @ConditionalOnMissingBean(GovernanceAuthorizationPort.class)
  GovernanceAuthorizationPort denyAllGovernanceAuthorization() {
    return (op, actor) -> Mono.just(AuthorizationDecision.DENY);
  }
}
