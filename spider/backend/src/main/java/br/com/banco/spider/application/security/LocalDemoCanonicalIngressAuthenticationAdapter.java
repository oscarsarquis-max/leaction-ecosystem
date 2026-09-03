package br.com.banco.spider.application.security;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import reactor.core.publisher.Mono;

/** Autentica somente a credencial allowlist do local-demo. Ausência ou valor estranho → empty. */
public class LocalDemoCanonicalIngressAuthenticationAdapter
    implements CanonicalIngressAuthenticationPort {

  @Override
  public Mono<Optional<AuthenticatedOriginator>> authenticate(IngressAuthenticationRequest request) {
    if (request == null || !LocalDemoCanonicalCredentials.credentialAllowed(request.credentialMaterialRef())) {
      return Mono.just(Optional.empty());
    }
    Instant now = request.receivedAt() == null ? Instant.now() : request.receivedAt();
    return Mono.just(
        Optional.of(
            new AuthenticatedOriginator(
                LocalDemoCanonicalCredentials.PRINCIPAL_REF,
                LocalDemoCanonicalCredentials.ORIGINATOR_ID,
                LocalDemoCanonicalCredentials.CHANNEL,
                "LOCAL_DEMO",
                now.minusSeconds(1),
                now.plusSeconds(3600),
                List.of(LocalDemoCanonicalCredentials.CAPABILITY + ":*"),
                "profile:ingress:local-demo@1.0",
                "ev-local-demo")));
  }
}
