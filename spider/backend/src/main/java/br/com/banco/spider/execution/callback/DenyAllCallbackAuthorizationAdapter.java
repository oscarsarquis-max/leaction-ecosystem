package br.com.banco.spider.execution.callback;

import br.com.banco.spider.application.security.AuthorizationDecision;
import reactor.core.publisher.Mono;

/** Default seguro — nunca permite callback sem policy configurada. */
public class DenyAllCallbackAuthorizationAdapter implements CallbackAuthorizationPort {

  @Override
  public Mono<AuthorizationDecision> authorize(CallbackAuthorizationRequest request) {
    return Mono.just(AuthorizationDecision.DENY);
  }
}
