package br.com.banco.spider.integration.inbound.http.satellite;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;

@SpringBootTest(
    properties = {
      "spider.context.ai.enabled=false",
      "spider.satellite.enabled=true",
      "spider.satellite.registry.segsense.secret=segsense-http-test-only",
      "spider.satellite.registry.spiderbank.secret=spiderbank-http-test-only",
      "spider.satellite.providers.insurance-provider-mock.secret=segsense-mock-http-test-only"
    })
@AutoConfigureWebTestClient(timeout = "PT30S")
@ActiveProfiles("local-demo")
class SpiderBankSatelliteInteractionHttpTest {

  private static final String SECRET = "spiderbank-http-test-only";

  @Autowired WebTestClient client;
  @MockBean ProviderCapabilityPort provider;

  @Test
  void wrongSecretIsUnauthenticated() {
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "spiderbank")
        .header("X-Spider-Satellite-Secret", "wrong")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(validEnvelope())
        .exchange()
        .expectStatus()
        .isUnauthorized();
    verify(provider, never()).execute(any());
  }

  @Test
  void confirmedObjectiveReturnsPlanImpediments() {
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "spiderbank")
        .header("X-Spider-Satellite-Secret", SECRET)
        .header("X-Correlation-ID", "22222222-2222-2222-2222-222222222222")
        .header("Idempotency-Key", "idem-http-credit-1")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(validEnvelope())
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.contractVersion")
        .isEqualTo("1.0")
        .jsonPath("$.status")
        .isEqualTo("PLAN_IMPEDED")
        .jsonPath("$.requiredAction")
        .isEqualTo("PRESENT_PLAN_IMPEDIMENTS")
        .jsonPath("$.correlationId")
        .isEqualTo("22222222-2222-2222-2222-222222222222")
        .jsonPath("$.originProvenance.sourceId")
        .isEqualTo("SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1")
        .jsonPath("$.resultSummary.intent")
        .isEqualTo("SEEK_WORKING_CAPITAL")
        .jsonPath("$.resultSummary.planId")
        .isEqualTo("WORKING_CAPITAL_DIAGNOSTIC_V1")
        .jsonPath("$.resultSummary.analysisComplete")
        .isEqualTo(false)
        .jsonPath("$.resultSummary.impediments.length()")
        .isEqualTo(7)
        .jsonPath("$.planId")
        .doesNotExist()
        .jsonPath("$.executionId")
        .doesNotExist();
    verify(provider, never()).execute(any());
  }

  @Test
  @SuppressWarnings("unchecked")
  void forgedSourceIsRejected() {
    Map<String, Object> body = validEnvelope();
    Map<String, Object> context = new LinkedHashMap<>((Map<String, Object>) body.get("context"));
    Map<String, Object> snapshot = new LinkedHashMap<>((Map<String, Object>) context.get("snapshot"));
    Map<String, Object> provenance = new LinkedHashMap<>((Map<String, Object>) snapshot.get("provenance"));
    provenance.put("sourceId", "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1");
    snapshot.put("provenance", provenance);
    context.put("snapshot", snapshot);
    body.put("context", context);
    body.put("idempotencyKey", "idem-http-credit-forged");
    body.put("messageId", "msg-http-credit-forged");
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "spiderbank")
        .header("X-Spider-Satellite-Secret", SECRET)
        .header("X-Correlation-ID", "22222222-2222-2222-2222-222222222222")
        .header("Idempotency-Key", "idem-http-credit-forged")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isBadRequest()
        .expectBody()
        .jsonPath("$.errorCode")
        .isEqualTo("INVALID_PAYLOAD");
    verify(provider, never()).execute(any());
  }

  private static Map<String, Object> validEnvelope() {
    Map<String, Object> envelope = new LinkedHashMap<>();
    envelope.put("contractVersion", "1.0");
    envelope.put("messageId", "msg-http-credit-1");
    envelope.put("correlationId", "22222222-2222-2222-2222-222222222222");
    envelope.put("satelliteId", "spiderbank");
    envelope.put("satelliteRole", "EXPERIENCE");
    envelope.put("interactionType", "REQUEST_DECISION");
    envelope.put("createdAt", "2026-09-18T12:00:00Z");
    envelope.put("idempotencyKey", "idem-http-credit-1");
    envelope.put("purpose", "WORKING_CAPITAL_ASSESSMENT");
    envelope.put(
        "objective",
        Map.of(
            "text",
            "SEEK_WORKING_CAPITAL",
            "origin",
            "USER_DECLARED",
            "declaredAt",
            "2026-09-18T12:00:00Z"));
    envelope.put(
        "context",
        Map.of(
            "snapshot",
            Map.of(
                "schemaVersion",
                "1.0",
                "classification",
                "INTERNAL",
                "nonPersonal",
                true,
                "provenance",
                Map.of(
                    "sourceType",
                    "SATELLITE_GOVERNED",
                    "sourceId",
                    "SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1",
                    "sourceTimestamp",
                    "2026-09-18T12:00:00Z",
                    "captureMethod",
                    "SERVER_REGISTRY",
                    "trustLevel",
                    "GOVERNED"),
                "attributes",
                Map.of(
                    "channel",
                    "SPIDERBANK_PUBLIC_DEMO",
                    "purposeVersion",
                    "demo-working-capital-v1",
                    "theme",
                    "working_capital",
                    "situation",
                    "synthetic_working_capital_need",
                    "need",
                    "assess_working_capital",
                    "horizon",
                    "months"))));
    envelope.put("dataClassification", "INTERNAL");
    envelope.put("responseChannel", "SYNC");
    envelope.put("metadata", Map.of());
    return envelope;
  }
}
