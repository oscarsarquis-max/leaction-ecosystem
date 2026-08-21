package br.com.banco.spider.execution.callback;

import br.com.banco.spider.application.security.AuthorizationDecision;
import reactor.core.publisher.Mono;

/** Adapter de teste: permite se originador está na definição e projection bate. */
public class OriginatorMatchedCallbackAuthorizationAdapter implements CallbackAuthorizationPort {

  @Override
  public Mono<AuthorizationDecision> authorize(CallbackAuthorizationRequest request) {
    if (request.callbackDefinition() == null || request.originatorId() == null) {
      return Mono.just(AuthorizationDecision.DENY);
    }
    boolean originatorOk =
        request.callbackDefinition().allowedOriginatorRefs().contains(request.originatorId());
    boolean projectionOk =
        request.projectionRef() == null
            || request.projectionRef().equals(request.callbackDefinition().projectionRef());
    if (!originatorOk || !projectionOk) {
      return Mono.just(AuthorizationDecision.DENY);
    }
    return Mono.just(AuthorizationDecision.PERMIT);
  }
}
