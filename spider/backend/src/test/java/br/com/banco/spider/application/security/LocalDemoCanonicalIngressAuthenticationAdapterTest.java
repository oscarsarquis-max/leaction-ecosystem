package br.com.banco.spider.application.security;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class LocalDemoCanonicalIngressAuthenticationAdapterTest {

  private final LocalDemoCanonicalIngressAuthenticationAdapter auth =
      new LocalDemoCanonicalIngressAuthenticationAdapter();
  private final Instant now = Instant.parse("2026-09-03T12:00:00Z");

  @Test
  void blankCredentialRemainsUnauthenticated() {
    StepVerifier.create(auth.authenticate(request(null)))
        .assertNext(opt -> assertTrue(opt.isEmpty()))
        .verifyComplete();
  }

  @Test
  void unknownCredentialRemainsUnauthenticated() {
    StepVerifier.create(auth.authenticate(request("cred:other")))
        .assertNext(opt -> assertTrue(opt.isEmpty()))
        .verifyComplete();
  }

  @Test
  void allowlistedCredentialAuthenticatesDemoOriginator() {
    StepVerifier.create(auth.authenticate(request(LocalDemoCanonicalCredentials.CREDENTIAL_REF)))
        .assertNext(
            opt -> {
              AuthenticatedOriginator originator = opt.orElseThrow();
              assertEquals(LocalDemoCanonicalCredentials.PRINCIPAL_REF, originator.principalRef());
              assertEquals(LocalDemoCanonicalCredentials.ORIGINATOR_ID, originator.originatorId());
              assertEquals(LocalDemoCanonicalCredentials.CHANNEL, originator.channel());
            })
        .verifyComplete();
  }

  private IngressAuthenticationRequest request(String credential) {
    return new IngressAuthenticationRequest("REST_HTTP", credential, Map.of(), null, now);
  }
}
