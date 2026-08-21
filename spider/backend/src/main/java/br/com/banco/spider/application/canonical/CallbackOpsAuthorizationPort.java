package br.com.banco.spider.application.canonical;

import br.com.banco.spider.application.security.AuthorizationDecision;
import reactor.core.publisher.Mono;

public interface CallbackOpsAuthorizationPort {
  Mono<AuthorizationDecision> authorize(String operationCode, String actorRef);
}
