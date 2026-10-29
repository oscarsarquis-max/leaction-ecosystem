package br.com.banco.spider.integration.inbound.http.satellite;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.time.Instant;
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
      "spider.satellite.registry.lojadepaes.secret=loja-biblioteca-http-test-only",
      "spider.satellite.registry.actionfinance.secret=actionfinance-http-test-only",
      "spider.satellite.providers.actionhub-biblioteca.secret=biblioteca-provider-http-test-only"
    })
@AutoConfigureWebTestClient(timeout = "PT30S")
@ActiveProfiles("local-demo")
class LojaBibliotecaSatelliteInteractionHttpTest {

  private static final String SECRET = "loja-biblioteca-http-test-only";

  @Autowired WebTestClient client;
  @MockBean ProviderCapabilityPort provider;

  @Test
  void catalogDispatchesListHubCatalog() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-1",
                    "actionhub-biblioteca",
                    null,
                    "ACTIONHUB_BIBLIOTECA",
                    SatelliteContractV1.WATERMARK_BIBLIOTECA,
                    List.of(),
                    List.of(),
                    Map.of(
                        "app_id",
                        "lojadepaes",
                        "plans",
                        List.of(Map.of("sku", "LOJADEPAES_BIBLIOTECA_MENSAL", "price", 19))))));
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "lojadepaes")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(envelope("LIST_LOJA_PLANS", Map.of("appId", "lojadepaes")))
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("READY")
        .jsonPath("$.capabilityId")
        .isEqualTo("LIST_HUB_CATALOG")
        .jsonPath("$.spiderPath")
        .isEqualTo(SatelliteContractV1.PATH_V1_5)
        .jsonPath("$.resultSummary.app_id")
        .isEqualTo("lojadepaes")
        .jsonPath("$.states.satellite")
        .isEqualTo("READY")
        .jsonPath("$.states.technical")
        .isEqualTo("COMPLETED")
        .jsonPath("$.states.financial")
        .isEqualTo("not_applicable")
        .jsonPath("$.identities.satelliteId")
        .isEqualTo("lojadepaes");
    verify(provider)
        .execute(argThat(request -> SatelliteContractV1.LIST_HUB_CATALOG.equals(request.capabilityId())));
  }

  @Test
  void checkoutCreatesPendingFinanceWithoutCardAndDoesNotConfirm() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-checkout",
                    "actionhub-biblioteca",
                    "ord-9",
                    "ACTIONHUB_BIBLIOTECA",
                    SatelliteContractV1.WATERMARK_BIBLIOTECA,
                    List.of(),
                    List.of(),
                    Map.of(
                        "checkout_url",
                        "https://actionhub.com.br/dashboard?checkout=ord-9&email=cliente@loja.test",
                        "order_id",
                        "ord-9",
                        "sku",
                        "LOJADEPAES_BIBLIOTECA_CREDITOS",
                        "checkout_mode",
                        "hub_brick"))));
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "lojadepaes")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(
            envelope(
                "START_LOJA_CHECKOUT",
                Map.of("appId", "lojadepaes", "subjectId", "cliente@loja.test", "sku", "LOJADEPAES_BIBLIOTECA_CREDITOS"),
                "loja-test-checkout-0001",
                "checkout:lojadepaes:CREDITOS"))
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("READY")
        .jsonPath("$.capabilityId")
        .isEqualTo("START_HUB_CATALOG_CHECKOUT")
        .jsonPath("$.states.financial")
        .isEqualTo("pending")
        .jsonPath("$.states.commercial")
        .isEqualTo("pending")
        .jsonPath("$.nextInteraction")
        .isEqualTo("GET_LOJA_ENTITLEMENTS")
        .jsonPath("$.resultSummary.checkout_url")
        .value(url -> org.assertj.core.api.Assertions.assertThat(String.valueOf(url)).doesNotContain("cliente@"))
        .jsonPath("$.resultSummary.checkout_url")
        .value(url -> org.assertj.core.api.Assertions.assertThat(String.valueOf(url)).doesNotContain("card"));
  }

  @Test
  void checkoutTimeoutAsksRecoveryWithoutNewDebit() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    false,
                    "UNKNOWN",
                    "preq-to",
                    "actionhub-biblioteca",
                    null,
                    "ACTIONHUB_BIBLIOTECA",
                    SatelliteContractV1.WATERMARK_BIBLIOTECA,
                    List.of(),
                    List.of(),
                    Map.of("effectCertainty", "UNKNOWN"))));
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "lojadepaes")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(
            envelope(
                "START_LOJA_CHECKOUT",
                Map.of("appId", "lojadepaes", "subjectId", "cliente@loja.test", "sku", "LOJADEPAES_BIBLIOTECA_MENSAL"),
                "loja-test-timeout-0001",
                "checkout:lojadepaes:timeout"))
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("PROVIDER_UNAVAILABLE")
        .jsonPath("$.requiredAction")
        .isEqualTo("QUERY_STATUS")
        .jsonPath("$.states.technical")
        .isEqualTo("EFFECT_UNKNOWN")
        .jsonPath("$.nextInteraction")
        .isEqualTo("LIST_LOJA_SUBSCRIPTIONS");
  }

  @Test
  void reserveCreditsReturnsHubReservationState() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-res",
                    "actionhub-biblioteca",
                    null,
                    "ACTIONHUB_BIBLIOTECA",
                    SatelliteContractV1.WATERMARK_BIBLIOTECA,
                    List.of(),
                    List.of(),
                    Map.of("ok", true, "status", "reserved", "idempotent", true, "credits", 19))));
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "lojadepaes")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(
            envelope(
                "RESERVE_LOJA_CREDITS",
                Map.of("appId", "lojadepaes", "subjectId", "cliente@loja.test", "operationId", "consulta-ia-0001"),
                "loja-test-reserve-0001",
                "reserve:lojadepaes:consulta-ia-0001"))
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.capabilityId")
        .isEqualTo("RESERVE_HUB_CREDITS")
        .jsonPath("$.states.commercial")
        .isEqualTo("reserved")
        .jsonPath("$.states.financial")
        .isEqualTo("not_applicable")
        .jsonPath("$.resultSummary.idempotent")
        .isEqualTo(true);
  }

  @Test
  void incompatibleContractVersionIsRejected() {
    Map<String, Object> body = envelope("LIST_LOJA_PLANS", Map.of("appId", "lojadepaes"));
    body.put("contractVersion", "1.4");
    body.put("purpose", "FINANCIAL_EXTERNAL_LOOKUP");
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "lojadepaes")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isBadRequest();
    verify(provider, never()).execute(any());
  }

  @Test
  void missingSubjectIdBlocksMutatingCapability() {
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "lojadepaes")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(
            envelope(
                "RESERVE_LOJA_CREDITS",
                Map.of("appId", "lojadepaes"),
                "loja-test-nosubject-0001",
                "reserve:lojadepaes:missing-subject"))
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("MISSING_CONTEXT");
    verify(provider, never()).execute(any());
  }

  @Test
  void actionFinanceCannotUseBibliotecaPurpose() {
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", "actionfinance-http-test-only")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(envelope("LIST_LOJA_PLANS", Map.of("appId", "lojadepaes")))
        .exchange()
        .expectStatus()
        .isForbidden();
    verify(provider, never()).execute(any());
  }

  @Test
  void foreignAppIdIsRejectedByContract() {
    Map<String, Object> body = envelope("LIST_LOJA_PLANS", Map.of("appId", "inove4us"));
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "lojadepaes")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isBadRequest();
    verify(provider, never()).execute(any());
  }

  private static Map<String, Object> envelope(String objective, Map<String, Object> biblioteca) {
    return envelope(objective, biblioteca, "loja-test-catalog-0001", "catalog:lojadepaes:" + objective);
  }

  private static Map<String, Object> envelope(
      String objective, Map<String, Object> biblioteca, String messageId, String idempotencyKey) {
    String now = Instant.parse("2026-10-08T21:00:00Z").toString();
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contractVersion", "1.5");
    body.put("messageId", messageId);
    body.put("correlationId", "loja-corr-catalog-0001");
    body.put("satelliteId", "lojadepaes");
    body.put("satelliteRole", "EXPERIENCE");
    body.put("interactionType", "QUERY_STATUS");
    body.put("createdAt", now);
    body.put("idempotencyKey", idempotencyKey);
    body.put("purpose", "LOJA_BIBLIOTECA");
    body.put("objective", Map.of("text", objective, "origin", "SATELLITE_GOVERNED", "declaredAt", now));
    body.put("dataClassification", "INTERNAL");
    body.put("responseChannel", "SYNC");
    body.put(
        "context",
        Map.of(
            "snapshot",
            Map.of(
                "schemaVersion",
                "1.5",
                "classification",
                "INTERNAL",
                "nonPersonal",
                true,
                "provenance",
                Map.of(
                    "sourceType",
                    "SATELLITE_GOVERNED",
                    "sourceId",
                    "LOJADEPAES_BIBLIOTECA_V1",
                    "sourceTimestamp",
                    now,
                    "captureMethod",
                    "SERVER_REGISTRY",
                    "trustLevel",
                    "GOVERNED"),
                "selectedContribution",
                "GOVERNED_SOURCE",
                "contributions",
                List.of(
                    Map.of(
                        "role",
                        "GOVERNED_SOURCE",
                        "sourceType",
                        "SATELLITE_GOVERNED",
                        "sourceId",
                        "LOJADEPAES_BIBLIOTECA_V1",
                        "sourceTimestamp",
                        now,
                        "captureMethod",
                        "SERVER_REGISTRY",
                        "trustLevel",
                        "GOVERNED",
                        "used",
                        true,
                        "elements",
                        Map.of("theme", "biblioteca_plans"))),
                "attributes",
                Map.of("channel", "LOJADEPAES", "theme", "biblioteca_plans", "appId", "lojadepaes", "purposeVersion", "biblioteca-v1"))));
    body.put("extensions", Map.of("biblioteca", biblioteca));
    return body;
  }
}
