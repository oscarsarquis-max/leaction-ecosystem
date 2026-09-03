package br.com.banco.spider.integration.inbound.http.canonical;

import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.LocalDemoCanonicalCredentials;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;

@SpringBootTest
@AutoConfigureWebTestClient
@ActiveProfiles("local-demo")
class LocalDemoCanonicalHttpAccessTest {

  @Autowired WebTestClient client;

  @Test
  void listWithoutCredentialIsUnauthorized() {
    client
        .get()
        .uri("/v1/canonical/executions")
        .exchange()
        .expectStatus()
        .isUnauthorized()
        .expectBody()
        .jsonPath("$.code")
        .isEqualTo("UNAUTHENTICATED");
  }

  @Test
  void listWithAllowlistedCredentialReturnsOwnedExecutions() {
    client
        .get()
        .uri("/v1/canonical/executions")
        .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.items")
        .isArray()
        .jsonPath("$.items[?(@.executionId=='demo-retry-001')]")
        .isNotEmpty();
  }

  @Test
  void unknownCredentialDoesNotOpenIngress() {
    client
        .get()
        .uri("/v1/canonical/executions")
        .header("X-Spider-Credential-Ref", "cred:stranger")
        .exchange()
        .expectStatus()
        .isUnauthorized();
  }

  @Test
  void legacyOrchestrateRemainsMapped() {
    client
        .post()
        .uri("/v1/products/orchestrate")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(Map.of())
        .exchange()
        .expectStatus()
        .value(status -> assertTrue(status != 404));
  }

  @Test
  void faviconIsPresent() {
    client.get().uri("/favicon.ico").exchange().expectStatus().isOk();
  }

  @Test
  void submitWithoutExecutionIdDoesNotReturn500() {
    java.util.Map<String, Object> execution = new java.util.HashMap<>();
    execution.put("executionId", null);
    execution.put("requestedAt", "2026-09-03T12:00:00Z");
    execution.put("idempotencyKey", "idem-home-null-id");
    java.util.Map<String, Object> body = new java.util.HashMap<>();
    body.put("contract", Map.of("schemaVersion", "1.0", "contractVersion", "1.0.0"));
    body.put("execution", execution);
    body.put(
        "contextRef",
        Map.of(
            "contextId",
            "ctx-RETRY_THEN_SUCCESS",
            "intentId",
            "intent:demo",
            "capabilityId",
            "capability:mock",
            "productServiceId",
            "product:mock",
            "journeyId",
            "journey:mock"));
    body.put(
        "origin",
        Map.of(
            "channel",
            "operational-console",
            "originatorId",
            "console-local-demo",
            "interactionRef",
            "corr-home-null-id"));
    body.put(
        "trace",
        Map.of(
            "correlationId",
            "corr-home-null-id",
            "traceparent",
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"));
    body.put("target", Map.of("capability", "mock", "operation", "RETRY_THEN_SUCCESS"));
    body.put("payload", Map.of("canonicalData", Map.of("mockScenario", "RETRY_THEN_SUCCESS")));

    client
        .post()
        .uri("/v1/canonical/executions")
        .contentType(MediaType.APPLICATION_JSON)
        .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
        .header("Idempotency-Key", "idem-home-null-id")
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .is2xxSuccessful();
  }
}
