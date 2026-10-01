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
      "spider.satellite.registry.actionfinance.secret=actionfinance-http-test-only",
      "spider.satellite.providers.actionhub-pay.secret=actionhub-pay-http-test-only"
    })
@AutoConfigureWebTestClient(timeout = "PT30S")
@ActiveProfiles("local-demo")
class ActionFinanceSatelliteInteractionHttpTest {

  private static final String SECRET = "actionfinance-http-test-only";
  private static final String COMPANY = "11111111-1111-4111-a111-111111111111";

  @Autowired WebTestClient client;
  @MockBean ProviderCapabilityPort provider;

  @Test
  void authenticatedLookupDispatchesSelectedCapability() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-1",
                    "actionhub-pay",
                    "pay-homolog-0001",
                    "SIMULATOR",
                    SatelliteContractV1.WATERMARK_FINANCIAL,
                    List.of(),
                    List.of(),
                    Map.of(
                        "kind",
                        "EXTERNAL_PAYMENT_LOOKUP",
                        "externalStatus",
                        "CONFIRMED",
                        "amountMinor",
                        12550,
                        "currency",
                        "BRL",
                        "origin",
                        "SIMULATOR"))));
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(lookupEnvelope(COMPANY, "pay-homolog-0001", true))
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("READY")
        .jsonPath("$.capabilityId")
        .isEqualTo("LOOKUP_ACTIONHUB_PAYMENT")
        .jsonPath("$.requiredAction")
        .isEqualTo("PRESENT_EXTERNAL_LOOKUP")
        .jsonPath("$.spiderPath")
        .isEqualTo(SatelliteContractV1.PATH_V1_3)
        .jsonPath("$.correlationId")
        .isEqualTo("afc-corr-lookup-0001")
        .jsonPath("$.resultSummary.origin")
        .isEqualTo("SIMULATOR");
    verify(provider)
        .execute(
            argThat(
                request ->
                    "LOOKUP_ACTIONHUB_PAYMENT".equals(request.capabilityId())
                        && "homolog-padaria".equals(request.capabilityInputs().get("payAppId"))
                        && COMPANY.equals(request.capabilityInputs().get("companyId"))));
  }

  @Test
  void experienceCannotExecuteCapability() {
    Map<String, Object> body = lookupEnvelope(COMPANY, "pay-homolog-0001", true);
    body.put("interactionType", "EXECUTE_CAPABILITY");
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isForbidden();
    verify(provider, never()).execute(any());
  }

  @Test
  void foreignCompanyIsRejectedBeforeProvider() {
    String other = "22222222-2222-4222-a222-222222222222";
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(lookupEnvelope(other, "pay-homolog-0001", false))
        .exchange()
        .expectStatus()
        .isForbidden();
    verify(provider, never()).execute(any());
  }

  @Test
  void authenticatedListDispatchesSelectedCapability() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-list-1",
                    "actionhub-pay",
                    null,
                    "ACTIONHUB_PAY",
                    SatelliteContractV1.WATERMARK_FINANCIAL,
                    List.of(),
                    List.of(),
                    Map.of(
                        "kind",
                        "EXTERNAL_PAYMENT_LIST",
                        "itemCount",
                        2,
                        "environment",
                        "HOMOLOG",
                        "origin",
                        "ACTIONHUB_PAY",
                        "importPersisted",
                        false))));
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(listEnvelope(COMPANY, true))
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("READY")
        .jsonPath("$.capabilityId")
        .isEqualTo("LIST_PAYMENT_TRANSACTIONS")
        .jsonPath("$.requiredAction")
        .isEqualTo("PRESENT_EXTERNAL_LIST")
        .jsonPath("$.spiderPath")
        .isEqualTo(SatelliteContractV1.PATH_V1_4)
        .jsonPath("$.resultSummary.itemCount")
        .isEqualTo(2)
        .jsonPath("$.resultSummary.importPersisted")
        .isEqualTo(false);
    verify(provider)
        .execute(
            argThat(
                request ->
                    "LIST_PAYMENT_TRANSACTIONS".equals(request.capabilityId())
                        && "homolog-padaria".equals(request.capabilityInputs().get("payAppId"))
                        && COMPANY.equals(request.capabilityInputs().get("companyId"))
                        && "HOMOLOG".equals(request.capabilityInputs().get("environment"))));
  }

  @Test
  void listForeignCompanyIsRejectedBeforeProvider() {
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(listEnvelope("22222222-2222-4222-a222-222222222222", false))
        .exchange()
        .expectStatus()
        .isForbidden();
    verify(provider, never()).execute(any());
  }

  @Test
  void insurancePurposeIsRejectedForActionFinance() {
    Map<String, Object> body = lookupEnvelope(COMPANY, "pay-homolog-0001", true);
    body.put("purpose", "INSURANCE_PROTECTION_ASSESSMENT");
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isForbidden();
    verify(provider, never()).execute(any());
  }

  private static Map<String, Object> lookupEnvelope(
      String companyId, String reference, boolean includeCompanyAttribute) {
    String now = Instant.parse("2026-09-30T18:00:00Z").toString();
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contractVersion", "1.3");
    body.put("messageId", "afm-test-lookup-0001");
    body.put("correlationId", "afc-corr-lookup-0001");
    body.put("satelliteId", "actionfinance");
    body.put("satelliteRole", "EXPERIENCE");
    body.put("interactionType", "QUERY_STATUS");
    body.put("createdAt", now);
    body.put("idempotencyKey", "lookup:" + companyId + ":" + reference);
    body.put("purpose", "FINANCIAL_EXTERNAL_LOOKUP");
    body.put("objective", Map.of("text", "LOOKUP_EXTERNAL_PAYMENT", "origin", "SATELLITE_GOVERNED", "declaredAt", now));
    body.put("dataClassification", "INTERNAL");
    body.put("responseChannel", "SYNC");
    body.put(
        "context",
        Map.of(
            "snapshot",
            Map.of(
                "schemaVersion",
                "1.3",
                "classification",
                "INTERNAL",
                "nonPersonal",
                true,
                "provenance",
                Map.of(
                    "sourceType",
                    "SATELLITE_GOVERNED",
                    "sourceId",
                    "ACTIONFINANCE_FINANCIAL_LOOKUP_V1",
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
                        "ACTIONFINANCE_FINANCIAL_LOOKUP_V1",
                        "sourceTimestamp",
                        now,
                        "captureMethod",
                        "SERVER_REGISTRY",
                        "trustLevel",
                        "GOVERNED",
                        "used",
                        true,
                        "elements",
                        Map.of("theme", "payment_lookup"))),
                "attributes",
                attributes(companyId, includeCompanyAttribute))));
    body.put(
        "extensions",
        Map.of(
            "financialLookup",
            Map.of(
                "companyId",
                companyId,
                "externalReference",
                reference,
                "originSystem",
                "ACTIONHUB_PAY")));
    return body;
  }

  private static Map<String, Object> listEnvelope(String companyId, boolean includeCompanyAttribute) {
    String now = Instant.parse("2026-10-01T15:00:00Z").toString();
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contractVersion", "1.4");
    body.put("messageId", "afm-test-list-0001");
    body.put("correlationId", "afc-corr-list-0001");
    body.put("satelliteId", "actionfinance");
    body.put("satelliteRole", "EXPERIENCE");
    body.put("interactionType", "QUERY_STATUS");
    body.put("createdAt", now);
    body.put("idempotencyKey", "list:" + companyId + ":HOMOLOG");
    body.put("purpose", "FINANCIAL_EXTERNAL_LIST");
    body.put("objective", Map.of("text", "LIST_EXTERNAL_PAYMENTS", "origin", "SATELLITE_GOVERNED", "declaredAt", now));
    body.put("dataClassification", "INTERNAL");
    body.put("responseChannel", "SYNC");
    body.put(
        "context",
        Map.of(
            "snapshot",
            Map.of(
                "schemaVersion",
                "1.4",
                "classification",
                "INTERNAL",
                "nonPersonal",
                true,
                "provenance",
                Map.of(
                    "sourceType",
                    "SATELLITE_GOVERNED",
                    "sourceId",
                    "ACTIONFINANCE_FINANCIAL_LIST_V1",
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
                        "ACTIONFINANCE_FINANCIAL_LIST_V1",
                        "sourceTimestamp",
                        now,
                        "captureMethod",
                        "SERVER_REGISTRY",
                        "trustLevel",
                        "GOVERNED",
                        "used",
                        true,
                        "elements",
                        Map.of("theme", "payment_list"))),
                "attributes",
                listAttributes(companyId, includeCompanyAttribute))));
    body.put(
        "extensions",
        Map.of(
            "financialList",
            Map.of(
                "companyId",
                companyId,
                "originSystem",
                "ACTIONHUB_PAY",
                "environment",
                "HOMOLOG",
                "limit",
                2)));
    return body;
  }

  private static Map<String, String> listAttributes(String companyId, boolean includeCompanyAttribute) {
    Map<String, String> values = new LinkedHashMap<>();
    values.put("channel", "ACTIONFINANCE_HOMOLOG");
    values.put("purposeVersion", "financial-list-v1");
    values.put("theme", "payment_list");
    values.put("situation", "test_payment_list");
    values.put("need", "list_external_payments");
    values.put("horizon", "days");
    if (includeCompanyAttribute) {
      values.put("companyId", companyId);
    }
    return values;
  }

  private static Map<String, String> attributes(String companyId, boolean includeCompanyAttribute) {
    Map<String, String> values = new LinkedHashMap<>();
    values.put("channel", "ACTIONFINANCE_HOMOLOG");
    values.put("purposeVersion", "financial-lookup-v1");
    values.put("theme", "payment_lookup");
    values.put("situation", "test_payment_follow_up");
    values.put("need", "lookup_external_payment");
    values.put("horizon", "days");
    if (includeCompanyAttribute) {
      values.put("companyId", companyId);
    }
    return values;
  }
}
