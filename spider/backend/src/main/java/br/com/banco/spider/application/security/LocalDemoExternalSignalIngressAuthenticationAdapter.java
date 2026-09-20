package br.com.banco.spider.application.security;

import br.com.banco.spider.execution.signal.SignalSecurityContext;
import java.time.Instant;
import java.util.Optional;
import reactor.core.publisher.Mono;

/** Sinal Mock no local-demo: mesma credencial allowlist do console. */
public class LocalDemoExternalSignalIngressAuthenticationAdapter
    implements ExternalSignalIngressAuthenticationPort {

  @Override
  public Mono<Optional<SignalSecurityContext>> authenticate(IngressAuthenticationRequest request) {
    if (request == null || !LocalDemoCanonicalCredentials.credentialAllowed(request.credentialMaterialRef())) {
      return Mono.just(Optional.empty());
    }
    Instant now = request.receivedAt() == null ? Instant.now() : request.receivedAt();
    return Mono.just(
        Optional.of(
            new SignalSecurityContext(
                LocalDemoCanonicalCredentials.PRINCIPAL_REF,
                LocalDemoCanonicalCredentials.SIGNAL_SOURCE_REF,
                "LOCAL_DEMO",
                now.minusSeconds(1),
                now.plusSeconds(3600),
                LocalDemoCanonicalCredentials.SIGNAL_SECURITY_PROFILE_REF,
                "ev-local-demo-signal")));
  }
}
