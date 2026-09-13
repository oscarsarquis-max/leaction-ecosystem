package br.com.banco.spider.integration.inbound.http.satellite;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ResultItem;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@SpringBootTest(
    properties = {
      "spider.context.ai.enabled=false",
      "spider.satellite.enabled=true",
      "spider.satellite.registry.segsense.secret=segsense-http-test-only",
      "spider.satellite.providers.insurance-provider-mock.secret=segsense-mock-http-test-only"
    })
@AutoConfigureWebTestClient(timeout = "PT30S")
@ActiveProfiles("local-demo")
class SatelliteInteractionHttpTest {

  private static final String SECRET = "segsense-http-test-only";

  @Autowired WebTestClient client;
  @MockBean ProviderCapabilityPort provider;

  @Test
  void missingIdentityIsUnauthenticated() {
    client
        .post()
        .uri("/v1/satellites/interactions")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(Map.of())
        .exchange()
        .expectStatus()
        .isUnauthorized()
        .expectBody()
        .jsonPath("$.errorCode")
        .isEqualTo("UNAUTHENTICATED");
  }

  @Test
  void wrongSecretIsUnauthenticated() {
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "segsense")
        .header("X-Spider-Satellite-Secret", "wrong")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(validEnvelope())
        .exchange()
        .expectStatus()
        .isUnauthorized();
  }

  @Test
  void invalidSchemaIsRejected() {
    Map<String, Object> body = validEnvelope();
    body.put("intent", "not-allowed");
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "segsense")
        .header("X-Spider-Satellite-Secret", SECRET)
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

  @Test
  void happyPathUsesCanonicalEnvelope() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-http",
                    "insurance-provider-mock",
                    "ill-9",
                    "ILLUSTRATIVE_NOT_ICATU_CONTRACT",
                    "DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO",
                    List.of(new ResultItem("STEP", "Revisar", "JOURNEY_STEP", true)),
                    List.of("Pendência"))));
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "segsense")
        .header("X-Spider-Satellite-Secret", SECRET)
        .header("X-Correlation-ID", "11111111-1111-1111-1111-111111111111")
        .header("Idempotency-Key", "idem-http-ok-1")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(validEnvelope())
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.contractVersion")
        .isEqualTo("1.0")
        .jsonPath("$.status")
        .isEqualTo("READY")
        .jsonPath("$.originProvenance.sourceType")
        .isEqualTo("SATELLITE_GOVERNED")
        .jsonPath("$.planId")
        .doesNotExist()
        .jsonPath("$.executionId")
        .doesNotExist();
  }

  private static Map<String, Object> validEnvelope() {
    Map<String, Object> envelope = new LinkedHashMap<>();
    envelope.put("contractVersion", "1.0");
    envelope.put("messageId", "msg-http-ok-1");
    envelope.put("correlationId", "11111111-1111-1111-1111-111111111111");
    envelope.put("satelliteId", "segsense");
    envelope.put("satelliteRole", "EXPERIENCE");
    envelope.put("interactionType", "REQUEST_DECISION");
    envelope.put("createdAt", "2026-09-13T12:00:00Z");
    envelope.put("idempotencyKey", "idem-http-ok-1");
    envelope.put("purpose", "INSURANCE_PROTECTION_ASSESSMENT");
    envelope.put(
        "objective",
        Map.of(
            "text",
            "UNDERSTAND_FAMILY_PROTECTION_OPTIONS",
            "origin",
            "SATELLITE_GOVERNED",
            "declaredAt",
            "2026-09-13T12:00:00Z"));
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
                    "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
                    "sourceTimestamp",
                    "2026-09-13T12:00:00Z",
                    "captureMethod",
                    "SERVER_REGISTRY",
                    "trustLevel",
                    "GOVERNED"),
                "attributes",
                Map.of(
                    "channel",
                    "SEGSENSE_PUBLIC_DEMO",
                    "editorialPieceVersion",
                    "demo-editorial-v1",
                    "purposeVersion",
                    "demo-purpose-v1"))));
    envelope.put("dataClassification", "INTERNAL");
    envelope.put("responseChannel", "SYNC");
    envelope.put("metadata", Map.of());
    return envelope;
  }
}
