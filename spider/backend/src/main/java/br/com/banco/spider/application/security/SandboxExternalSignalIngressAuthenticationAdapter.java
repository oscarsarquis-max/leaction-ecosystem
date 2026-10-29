package br.com.banco.spider.application.security;

import br.com.banco.spider.execution.signal.SignalSecurityContext;
import java.time.Instant;
import java.util.Optional;
import reactor.core.publisher.Mono;

/** Sinal mock no sandbox: mesma credencial allowlist do console, origem controlada. */
public class SandboxExternalSignalIngressAuthenticationAdapter
    implements ExternalSignalIngressAuthenticationPort {

  @Override
  public Mono<Optional<SignalSecurityContext>> authenticate(IngressAuthenticationRequest request) {
    if (request == null
        || !SandboxCanonicalCredentials.credentialAllowed(request.credentialMaterialRef())) {
      return Mono.just(Optional.empty());
    }
    Instant now = request.receivedAt() == null ? Instant.now() : request.receivedAt();
    return Mono.just(
        Optional.of(
            new SignalSecurityContext(
                SandboxCanonicalCredentials.PRINCIPAL_REF,
                SandboxCanonicalCredentials.SIGNAL_SOURCE_REF,
                "SANDBOX",
                now.minusSeconds(1),
                now.plusSeconds(3600),
                SandboxCanonicalCredentials.SIGNAL_SECURITY_PROFILE_REF,
                "ev-sandbox-signal")));
  }
}
