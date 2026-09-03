package br.com.banco.spider.application.security;

import reactor.core.publisher.Mono;

/** Autoriza apenas capability/operation Mock da allowlist. Qualquer outro alvo permanece DENY. */
public class LocalDemoCanonicalExecutionAuthorizationAdapter
    implements CanonicalExecutionAuthorizationPort {

  @Override
  public Mono<AuthorizationDecision> authorize(ExecutionAuthorizationRequest request) {
    if (request == null || request.authenticatedOriginator() == null) {
      return Mono.just(AuthorizationDecision.DENY);
    }
    if (!LocalDemoCanonicalCredentials.PRINCIPAL_REF.equals(
        request.authenticatedOriginator().principalRef())) {
      return Mono.just(AuthorizationDecision.DENY);
    }
    if (!LocalDemoCanonicalCredentials.CHANNEL.equals(request.channel())
        && !LocalDemoCanonicalCredentials.CHANNEL.equals(
            request.authenticatedOriginator().channel())) {
      return Mono.just(AuthorizationDecision.DENY);
    }
    boolean allowed =
        LocalDemoCanonicalCredentials.operationAllowed(
            request.capabilityCode(), request.operationCode());
    return Mono.just(allowed ? AuthorizationDecision.PERMIT : AuthorizationDecision.DENY);
  }
}
