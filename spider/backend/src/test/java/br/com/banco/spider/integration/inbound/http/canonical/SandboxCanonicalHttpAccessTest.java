package br.com.banco.spider.integration.inbound.http.canonical;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.SandboxCanonicalCredentials;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;

@SpringBootTest(
    properties = {
      "SPIDER_JWT_SECRET=sandbox-test-secret-key-material-32b"
    })
@AutoConfigureWebTestClient
@ActiveProfiles("sandbox")
class SandboxCanonicalHttpAccessTest {

  @Autowired WebTestClient client;

  @Test
  void listWithoutCredentialIsUnauthorized() {
    client
        .get()
        .uri("/v1/canonical/executions")
        .exchange()
        .expectStatus()
        .isUnauthorized();
  }

  @Test
  void unknownCredentialDoesNotOpenIngress() {
    client
        .get()
        .uri("/v1/canonical/executions")
        .header("X-Spider-Credential-Ref", "local-demo-console")
        .exchange()
        .expectStatus()
        .isUnauthorized();
  }

  @Test
  void consoleWithoutCredentialIsDenied() {
    client
        .get()
        .uri("/v1/console/executions")
        .exchange()
        .expectStatus()
        .isNotFound();
  }

  @Test
  void sandboxDemoRouteCreatesVisibleExecution() {
    Map<String, Object> submitted = submitDemo();
    assertEquals("SUCCEEDED", submitted.get("state"));
    Object executionId = submitted.get("executionId");
    assertNotNull(executionId);

    Map<?, ?> list =
        client
            .get()
            .uri("/v1/console/executions")
            .header("X-Spider-Credential-Ref", SandboxCanonicalCredentials.CREDENTIAL_REF)
            .exchange()
            .expectStatus()
            .isOk()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> items = (List<Map<String, Object>>) list.get("items");
    assertTrue(
        items.stream()
            .anyMatch(item -> String.valueOf(executionId).equals(item.get("executionId"))));
  }

  @Test
  void livenessIsPublic() {
    client.get().uri("/actuator/health/liveness").exchange().expectStatus().isOk();
  }

  @Test
  void disabledContextLookupIsNotFoundInsteadOfOrchestrationError() {
    Map<String, Object> submitted = submitDemo();
    String executionId = String.valueOf(submitted.get("executionId"));

    client
        .get()
        .uri("/v1/context/executions/" + executionId)
        .header("X-Spider-Credential-Ref", SandboxCanonicalCredentials.CREDENTIAL_REF)
        .exchange()
        .expectStatus()
        .isNotFound()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo(404)
        .jsonPath("$.title")
        .isEqualTo("Resource not found")
        .jsonPath("$.title")
        .value(title -> org.junit.jupiter.api.Assertions.assertNotEquals("Unexpected orchestration error", title));

    Map<?, ?> detail =
        client
            .get()
            .uri("/v1/console/executions/" + executionId)
            .header("X-Spider-Credential-Ref", SandboxCanonicalCredentials.CREDENTIAL_REF)
            .exchange()
            .expectStatus()
            .isOk()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    @SuppressWarnings("unchecked")
    Map<String, Object> summary = (Map<String, Object>) detail.get("summary");
    assertEquals("SUCCEEDED", summary.get("state"));
    assertEquals(executionId, String.valueOf(summary.get("executionId")));
  }

  @Test
  void multiStepDetailExposesDistinctStableAttempts() {
    Map<String, Object> submitted = submitDemo();
    String executionId = String.valueOf(submitted.get("executionId"));

    Map<?, ?> detail =
        client
            .get()
            .uri("/v1/console/executions/" + executionId)
            .header("X-Spider-Credential-Ref", SandboxCanonicalCredentials.CREDENTIAL_REF)
            .exchange()
            .expectStatus()
            .isOk()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();

    @SuppressWarnings("unchecked")
    Map<String, Object> stepsSection = (Map<String, Object>) detail.get("steps");
    assertEquals(Boolean.TRUE, stepsSection.get("available"));
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> steps = (List<Map<String, Object>>) stepsSection.get("data");
    assertEquals(2, steps.size());
    assertEquals("step-1", steps.get(0).get("stepRef"));
    assertEquals("step-2", steps.get(1).get("stepRef"));

    @SuppressWarnings("unchecked")
    List<Map<String, Object>> firstAttempts = (List<Map<String, Object>>) steps.get(0).get("attempts");
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> secondAttempts = (List<Map<String, Object>>) steps.get(1).get("attempts");
    assertEquals(1, firstAttempts.size());
    assertEquals(1, secondAttempts.size());
    assertEquals(1, ((Number) firstAttempts.get(0).get("attemptNumber")).intValue());
    assertEquals(1, ((Number) secondAttempts.get(0).get("attemptNumber")).intValue());
    assertTrue(String.valueOf(detail).contains("SUCCEEDED"));
    assertTrue(!String.valueOf(detail).contains("password"));
    assertTrue(!String.valueOf(detail).contains("Bearer "));
  }

  @Test
  void relatedEventsQueryDoesNotFailForValidSandboxExecution() {
    Map<String, Object> submitted = submitDemo();
    String executionId = String.valueOf(submitted.get("executionId"));

    client
        .get()
        .uri("/v1/console/executions/" + executionId + "/events")
        .header("X-Spider-Credential-Ref", SandboxCanonicalCredentials.CREDENTIAL_REF)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.executionId")
        .isEqualTo(executionId)
        .jsonPath("$.items")
        .isArray();
  }

  private Map<String, Object> submitDemo() {
    String id = "exec-" + UUID.randomUUID();
    String idem = "idem-sandbox-" + UUID.randomUUID();
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contract", Map.of("schemaVersion", "1.0", "contractVersion", "1.0.0"));
    body.put(
        "execution",
        Map.of("executionId", id, "requestedAt", Instant.parse("2026-09-28T16:00:00Z").toString(), "idempotencyKey", idem));
    body.put(
        "contextRef",
        Map.of(
            "contextId",
            "ctx-SANDBOX_DEMO",
            "intentId",
            "intent:sandbox-demo",
            "capabilityId",
            "capability:mock",
            "productServiceId",
            "product:sandbox-demo",
            "journeyId",
            "journey:mock"));
    body.put(
        "origin",
        Map.of(
            "channel",
            SandboxCanonicalCredentials.CHANNEL,
            "originatorId",
            SandboxCanonicalCredentials.ORIGINATOR_ID,
            "interactionRef",
            "corr-" + id));
    body.put(
        "trace",
        Map.of(
            "correlationId",
            "corr-" + id,
            "traceparent",
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"));
    body.put(
        "target",
        Map.of(
            "capability",
            SandboxCanonicalCredentials.CAPABILITY,
            "operation",
            SandboxCanonicalCredentials.DEMO_OPERATION));
    body.put("payload", Map.of("canonicalData", Map.of("mockScenario", "SUCCESS", "scenario", "SANDBOX_DEMO")));

    Map<?, ?> response =
        client
            .post()
            .uri("/v1/canonical/executions")
            .contentType(MediaType.APPLICATION_JSON)
            .header("X-Spider-Credential-Ref", SandboxCanonicalCredentials.CREDENTIAL_REF)
            .header("Idempotency-Key", idem)
            .bodyValue(body)
            .exchange()
            .expectStatus()
            .is2xxSuccessful()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    @SuppressWarnings("unchecked")
    Map<String, Object> execution = (Map<String, Object>) response.get("execution");
    return execution == null ? Map.of() : execution;
  }
}
