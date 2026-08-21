package br.com.banco.spider.governance;

import br.com.banco.spider.application.security.AuthorizationDecision;
import reactor.core.publisher.Mono;

public interface GovernanceAuthorizationPort {
  Mono<AuthorizationDecision> authorize(String operationCode, String actorPrincipalRef);
}
