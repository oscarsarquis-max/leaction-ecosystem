package br.com.banco.spider.application.security;

import reactor.core.publisher.Mono;

public class DenyAllCanonicalExecutionAuthorizationAdapter
    implements CanonicalExecutionAuthorizationPort {

  @Override
  public Mono<AuthorizationDecision> authorize(ExecutionAuthorizationRequest request) {
    return Mono.just(AuthorizationDecision.DENY);
  }
}
