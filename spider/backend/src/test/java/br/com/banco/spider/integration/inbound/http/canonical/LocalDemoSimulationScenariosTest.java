package br.com.banco.spider.integration.inbound.http.canonical;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.LocalDemoCanonicalCredentials;
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

@SpringBootTest
@AutoConfigureWebTestClient
@ActiveProfiles("local-demo")
class LocalDemoSimulationScenariosTest {

  @Autowired WebTestClient client;

  @Test
  void advertisesTheSixPublishedMonitorRoutes() {
    Map<?, ?> body =
        client
            .get()
            .uri("/v1/console/monitor/events")
            .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
            .exchange()
            .expectStatus()
            .isOk()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    assertEquals(
        List.of(
            "SUCCESS_MULTI_STEP",
            "RETRY_THEN_SUCCESS",
            "BUSINESS_NEGATIVE",
            "WAIT_SIGNAL_RESUME",
            "CALLBACK_RECONCILIATION",
            "TECHNICAL_FAILURE"),
        body.get("availableScenarios"));
  }

  @Test
  void multiStepRetryNegativeCallbackAndFailureCreateRealExecutions() {
    Map<String, Object> multi = submit("SUCCESS_MULTI_STEP", "SUCCESS");
    assertEquals("SUCCEEDED", multi.get("state"));
    assertTrue(listedInMonitor(multi.get("executionId")));
    assertTrue(stepCount(multi.get("executionId")) > 1);

    Map<String, Object> retry = submit("RETRY_THEN_SUCCESS", "RETRY_THEN_SUCCESS");
    assertEquals("SUCCEEDED", retry.get("state"));
    assertTrue(listedInMonitor(retry.get("executionId")));

    Map<String, Object> negative = submit("BUSINESS_NEGATIVE", "BUSINESS_NEGATIVE");
    assertEquals("SUCCEEDED", negative.get("state"));
    assertEquals("SUCCESS", String.valueOf(((Map<?, ?>) negative.get("outcome")).get("technicalStatus")));
    assertEquals(false, ((Map<?, ?>) ((Map<?, ?>) negative.get("outcome")).get("businessOutcome")).get("accepted"));
    assertTrue(listedInMonitor(negative.get("executionId")));

    Map<String, Object> callback = submit("CALLBACK_RECONCILIATION", "SUCCESS", "callback:console-local-demo");
    assertEquals("SUCCEEDED", callback.get("state"));
    assertTrue(listedInMonitor(callback.get("executionId")));

    Map<String, Object> failed = submitExpectingError("TECHNICAL_FAILURE", "TECHNICAL_FAILURE");
    assertNotNull(failed.get("executionId"));
    assertEquals("FAILED", failed.get("state"));
    assertTrue(listedInMonitor(failed.get("executionId")));
  }

  @Test
  void waitSignalResumeUsesTheExistingSignalIngress() {
    Map<String, Object> waiting = submit("WAIT_SIGNAL_RESUME", "ACCEPTED_ASYNC");
    assertEquals("WAITING_EXTERNAL", waiting.get("state"));
    String executionId = String.valueOf(waiting.get("executionId"));
    assertTrue(listedInMonitor(executionId));
    client
        .post()
        .uri("/v1/canonical/signals")
        .contentType(MediaType.APPLICATION_JSON)
        .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
        .bodyValue(signal(executionId))
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.processingStatus")
        .isEqualTo("ACCEPTED_AND_RESUMED")
        .jsonPath("$.executionId")
        .isEqualTo(executionId);
    assertTrue(listedInMonitor(executionId));
  }

  @Test
  void spiderbankCardUsesProductUrlAndDoesNotClaimIntegrationFromTheMockFlag() {
    Map<?, ?> body =
        client
            .get()
            .uri("/v1/console/monitor/simulation")
            .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
            .exchange()
            .expectStatus()
            .isOk()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> satellites = (List<Map<String, Object>>) body.get("satellites");
    Map<String, Object> bank =
        satellites.stream().filter(item -> "spiderbank".equals(item.get("id"))).findFirst().orElseThrow();
    assertEquals("http://127.0.0.1:5190/", bank.get("url"));
    assertFalse(String.valueOf(bank.get("missing")).contains("integratedWithSpider"));
    if (!Boolean.TRUE.equals(bank.get("available"))) {
      assertFalse(((java.util.List<?>) bank.get("missing")).isEmpty());
    }
  }

  private Map<String, Object> submit(String operation, String mockScenario) {
    return submit(operation, mockScenario, null);
  }

  private Map<String, Object> submit(String operation, String mockScenario, String callbackRef) {
    String idem = "idem-" + operation + "-" + UUID.randomUUID();
    Map<?, ?> body =
        client
            .post()
            .uri("/v1/canonical/executions")
            .contentType(MediaType.APPLICATION_JSON)
            .headers(headers -> headers(headers, idem))
            .bodyValue(request(operation, mockScenario, callbackRef, idem))
            .exchange()
            .expectStatus()
            .is2xxSuccessful()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    @SuppressWarnings("unchecked")
    Map<String, Object> execution = (Map<String, Object>) body.get("execution");
    assertNotNull(execution.get("executionId"));
    return Map.of(
        "executionId", execution.get("executionId"),
        "state", execution.get("state"),
        "outcome", body.get("outcome") == null ? Map.of() : body.get("outcome"));
  }

  private Map<String, Object> submitExpectingError(String operation, String mockScenario) {
    String idem = "idem-" + operation + "-" + UUID.randomUUID();
    Map<?, ?> body =
        client
            .post()
            .uri("/v1/canonical/executions")
            .contentType(MediaType.APPLICATION_JSON)
            .headers(headers -> headers(headers, idem))
            .bodyValue(request(operation, mockScenario, null, idem))
            .exchange()
            .expectStatus()
            .is5xxServerError()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    @SuppressWarnings("unchecked")
    Map<String, Object> execution = (Map<String, Object>) body.get("execution");
    return Map.of("executionId", execution.get("executionId"), "state", execution.get("state"));
  }

  private boolean listedInMonitor(Object executionId) {
    Map<?, ?> body =
        client
            .get()
            .uri("/v1/console/executions?limit=50")
            .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
            .exchange()
            .expectStatus()
            .isOk()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> items = (List<Map<String, Object>>) body.get("items");
    return items.stream().anyMatch(item -> String.valueOf(executionId).equals(item.get("executionId")));
  }

  private int stepCount(Object executionId) {
    Map<?, ?> body =
        client
            .get()
            .uri("/v1/console/executions/{id}", executionId)
            .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
            .exchange()
            .expectStatus()
            .isOk()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    @SuppressWarnings("unchecked")
    Map<String, Object> steps = (Map<String, Object>) body.get("steps");
    List<?> data = steps == null ? List.of() : (List<?>) steps.get("data");
    return data.size();
  }

  private void headers(org.springframework.http.HttpHeaders headers, String idempotencyKey) {
    headers.set("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF);
    headers.set("Idempotency-Key", idempotencyKey);
  }

  private Map<String, Object> request(
      String operation, String mockScenario, String callbackRef, String idempotencyKey) {
    String id = "exec-" + UUID.randomUUID();
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contract", Map.of("schemaVersion", "1.0", "contractVersion", "1.0.0"));
    body.put(
        "execution",
        Map.of(
            "executionId",
            id,
            "requestedAt",
            Instant.parse("2026-09-18T15:00:00Z").toString(),
            "idempotencyKey",
            idempotencyKey));
    body.put(
        "contextRef",
        Map.of(
            "contextId",
            "ctx-" + operation,
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
            "corr-" + id));
    body.put(
        "trace",
        Map.of(
            "correlationId",
            "corr-" + id,
            "traceparent",
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"));
    body.put("target", Map.of("capability", "mock", "operation", operation));
    body.put("payload", Map.of("canonicalData", Map.of("mockScenario", mockScenario)));
    if (callbackRef != null) {
      body.put("callbackRef", callbackRef);
    }
    return body;
  }

  private Map<String, Object> signal(String executionId) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("signalContractVersion", "1.0");
    body.put("messageId", "sig-" + UUID.randomUUID());
    body.put("sourceRef", "source:mock-async@1.0");
    body.put("bindingRef", "binding:mock-universal@1.0");
    body.put("contractRef", "contract:signal:async-completion@1.0");
    body.put("executionId", executionId);
    body.put("stepId", "step-1");
    body.put("externalOperationRef", "ext-op-" + executionId + "-step-1");
    body.put("occurredAt", Instant.now().toString());
    body.put("correlationId", "corr-signal-" + executionId);
    body.put(
        "completion",
        Map.of("disposition", "COMPLETED", "outcome", Map.of("technicalStatus", "SUCCESS"), "errors", List.of()));
    return body;
  }
}
