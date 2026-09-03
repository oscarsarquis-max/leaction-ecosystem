package br.com.banco.spider.integration.inbound.http.canonical;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.AuthenticatedOriginator;
import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.application.security.CanonicalExecutionAuthorizationPort;
import br.com.banco.spider.application.security.CanonicalIngressAuthenticationPort;
import br.com.banco.spider.application.security.ExecutionAuthorizationRequest;
import br.com.banco.spider.application.security.ExternalSignalIngressAuthenticationPort;
import br.com.banco.spider.application.security.IngressAuthenticationRequest;
import br.com.banco.spider.execution.signal.SignalSecurityContext;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteCatalogPort;
import br.com.banco.spider.execution.route.RouteDefinition;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@SpringBootTest
@AutoConfigureWebTestClient
@Import(CanonicalHttpProfileIntegrationTest.PermissiveAuth.class)
@TestPropertySource(
    properties = {
      "spider.canonical.http.enabled=true",
      "spider.canonical.http.status-query-enabled=true",
      "spider.canonical.signal-http.enabled=true",
      "spider.canonical.persistence.mode=memory",
      "spring.datasource.url=jdbc:h2:mem:spider_http_on;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class CanonicalHttpProfileIntegrationTest {

  @Autowired WebTestClient client;

  @TestConfiguration
  static class PermissiveAuth {
    private static final Instant NOW = Instant.parse("2026-07-21T12:00:00Z");

    @Bean
    @Primary
    CanonicalIngressAuthenticationPort testIngressAuth() {
      return req -> {
        if (req.credentialMaterialRef() == null || req.credentialMaterialRef().isBlank()) {
          return Mono.just(Optional.empty());
        }
        if (!"cred:test-originator".equals(req.credentialMaterialRef())) {
          return Mono.just(Optional.empty());
        }
        return Mono.just(
            Optional.of(
                new AuthenticatedOriginator(
                    "principal:test-http@1.0",
                    "orig-test",
                    "CH",
                    "test",
                    NOW.minusSeconds(10),
                    NOW.plusSeconds(3600),
                    List.of(CanonicalRouteFixtures.CAPABILITY + ":" + CanonicalRouteFixtures.OPERATION),
                    "profile:ingress:test@1.0",
                    "ev-http")));
      };
    }

    @Bean
    @Primary
    CanonicalExecutionAuthorizationPort testAuthz() {
      return (ExecutionAuthorizationRequest request) -> {
        if (request.authenticatedOriginator() == null) {
          return Mono.just(AuthorizationDecision.DENY);
        }
        String key = request.capabilityCode() + ":" + request.operationCode();
        boolean ok =
            request.authenticatedOriginator().allowedCapabilityRefs().contains(key)
                || request.authenticatedOriginator().allowedCapabilityRefs().stream()
                    .anyMatch(r -> r.startsWith(request.capabilityCode()));
        return Mono.just(ok ? AuthorizationDecision.PERMIT : AuthorizationDecision.DENY);
      };
    }

    @Bean
    @Primary
    ExternalSignalIngressAuthenticationPort testSignalAuth() {
      return (IngressAuthenticationRequest req) -> {
        if (!"cred:test-signal".equals(req.credentialMaterialRef())) {
          return Mono.just(Optional.empty());
        }
        return Mono.just(
            Optional.of(
                new SignalSecurityContext(
                    "principal:test-signal@1.0",
                    "source:mock-async@1.0",
                    "test",
                    NOW.minusSeconds(10),
                    NOW.plusSeconds(3600),
                    "profile:signal:test@1.0",
                    "ev-sig")));
      };
    }

    @Bean
    @Primary
    RouteCatalogPort testRoutes() {
      return new InMemoryRouteCatalog(
          List.<RouteDefinition>of(CanonicalRouteFixtures.publishedSingleStep("http-r", 1)));
    }
  }

  @Test
  void unauthenticatedListReturns401() {
    client.get().uri("/v1/canonical/executions").exchange().expectStatus().isUnauthorized();
  }

  @Test
  void unauthenticatedSubmissionReturns401() {
    client
        .post()
        .uri("/v1/canonical/executions")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(sampleBody("e-http-1"))
        .exchange()
        .expectStatus()
        .isUnauthorized();
  }

  @Test
  void authenticatedSubmissionSucceeds() {
    var result =
        client
            .post()
            .uri("/v1/canonical/executions")
            .contentType(MediaType.APPLICATION_JSON)
            .header("X-Spider-Credential-Ref", "cred:test-originator")
            .header("Idempotency-Key", "idem-e-http-ok")
            .bodyValue(sampleBody("e-http-ok"))
            .exchange()
            .expectBody(String.class)
            .returnResult();
    org.junit.jupiter.api.Assertions.assertTrue(
        result.getStatus().is2xxSuccessful(),
        "status=" + result.getStatus() + " body=" + result.getResponseBody());
    org.junit.jupiter.api.Assertions.assertEquals(
        "no-store", result.getResponseHeaders().getFirst("Cache-Control"));
  }

  @Test
  void originatorMismatchForbidden() {
    java.util.Map<String, Object> body = new java.util.HashMap<>(sampleBody("e-http-mis"));
    @SuppressWarnings("unchecked")
    java.util.Map<String, Object> origin =
        new java.util.HashMap<>((java.util.Map<String, Object>) body.get("origin"));
    origin.put("originatorId", "other-originator");
    body.put("origin", origin);
    client
        .post()
        .uri("/v1/canonical/executions")
        .contentType(MediaType.APPLICATION_JSON)
        .header("X-Spider-Credential-Ref", "cred:test-originator")
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isForbidden();
  }

  @Test
  void legacyOrchestrateStillPresent() {
    // smoke: mapping exists (may fail validation) — 4xx/5xx but not 404
    client.post().uri("/v1/products/orchestrate").exchange().expectStatus().value(s -> assertTrue(s != 404));
  }

  private static Map<String, Object> sampleBody(String executionId) {
    return Map.of(
        "contract", Map.of("schemaVersion", "1.0", "contractVersion", "1.0.0"),
        "execution",
            Map.of(
                "executionId",
                executionId,
                "requestedAt",
                "2026-07-21T12:00:00Z",
                "idempotencyKey",
                "idem-" + executionId),
        "contextRef",
            Map.of(
                "contextId",
                "c",
                "intentId",
                "i@1",
                "capabilityId",
                "cap@1",
                "productServiceId",
                "p@1",
                "journeyId",
                CanonicalRouteFixtures.JOURNEY),
        "origin", Map.of("channel", "CH", "originatorId", "orig-test"),
        "trace",
            Map.of(
                "correlationId",
                "corr-" + executionId,
                "traceparent",
                "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"),
        "target",
            Map.of(
                "capability",
                CanonicalRouteFixtures.CAPABILITY,
                "operation",
                CanonicalRouteFixtures.OPERATION),
        "payload", Map.of("canonicalData", Map.of("mockScenario", "SUCCESS")));
  }
}
