package br.com.banco.spider.application.security;

import reactor.core.publisher.Mono;

public interface CanonicalExecutionAuthorizationPort {
  Mono<AuthorizationDecision> authorize(ExecutionAuthorizationRequest request);
}
