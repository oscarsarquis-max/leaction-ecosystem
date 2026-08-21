package br.com.banco.spider.execution.callback;

import br.com.banco.spider.application.security.AuthorizationDecision;
import reactor.core.publisher.Mono;

public interface CallbackAuthorizationPort {
  Mono<AuthorizationDecision> authorize(CallbackAuthorizationRequest request);
}
