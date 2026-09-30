package br.com.banco.spider.application.security;

import reactor.core.publisher.Mono;

/** Autoriza apenas a rota de demonstração isolada do sandbox. Qualquer outro alvo permanece DENY. */
public class SandboxCanonicalExecutionAuthorizationAdapter
    implements CanonicalExecutionAuthorizationPort {

  @Override
  public Mono<AuthorizationDecision> authorize(ExecutionAuthorizationRequest request) {
    if (request == null || request.authenticatedOriginator() == null) {
      return Mono.just(AuthorizationDecision.DENY);
    }
    if (!SandboxCanonicalCredentials.PRINCIPAL_REF.equals(
        request.authenticatedOriginator().principalRef())) {
      return Mono.just(AuthorizationDecision.DENY);
    }
    if (!SandboxCanonicalCredentials.CHANNEL.equals(request.channel())
        && !SandboxCanonicalCredentials.CHANNEL.equals(
            request.authenticatedOriginator().channel())) {
      return Mono.just(AuthorizationDecision.DENY);
    }
    boolean allowed =
        SandboxCanonicalCredentials.operationAllowed(
            request.capabilityCode(), request.operationCode());
    return Mono.just(allowed ? AuthorizationDecision.PERMIT : AuthorizationDecision.DENY);
  }
}
