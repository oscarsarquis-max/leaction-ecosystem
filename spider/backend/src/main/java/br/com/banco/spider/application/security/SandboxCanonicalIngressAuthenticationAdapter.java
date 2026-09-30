package br.com.banco.spider.application.security;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import reactor.core.publisher.Mono;

/** Autentica somente a credencial allowlist do sandbox. Ausência ou valor estranho → empty. */
public class SandboxCanonicalIngressAuthenticationAdapter
    implements CanonicalIngressAuthenticationPort {

  @Override
  public Mono<Optional<AuthenticatedOriginator>> authenticate(IngressAuthenticationRequest request) {
    if (request == null
        || !SandboxCanonicalCredentials.credentialAllowed(request.credentialMaterialRef())) {
      return Mono.just(Optional.empty());
    }
    Instant now = request.receivedAt() == null ? Instant.now() : request.receivedAt();
    return Mono.just(
        Optional.of(
            new AuthenticatedOriginator(
                SandboxCanonicalCredentials.PRINCIPAL_REF,
                SandboxCanonicalCredentials.ORIGINATOR_ID,
                SandboxCanonicalCredentials.CHANNEL,
                "SANDBOX",
                now.minusSeconds(1),
                now.plusSeconds(3600),
                List.of(SandboxCanonicalCredentials.CAPABILITY + ":*"),
                "profile:ingress:sandbox@1.0",
                "ev-sandbox")));
  }
}
