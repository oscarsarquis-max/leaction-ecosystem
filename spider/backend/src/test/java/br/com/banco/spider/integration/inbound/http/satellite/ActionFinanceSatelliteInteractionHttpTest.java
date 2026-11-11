package br.com.banco.spider.integration.inbound.http.satellite;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
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
  void productionListIsAcceptedAndDispatchesSelectedCapability() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-list-prod-1",
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
                        0,
                        "reviewCount",
                        9,
                        "environment",
                        "PRODUCTION",
                        "origin",
                        "ACTIONHUB_PAY",
                        "importPersisted",
                        false))));
    Map<String, Object> body = listEnvelope(COMPANY, true);
    body.put("idempotencyKey", "list:" + COMPANY + ":PRODUCTION");
    body.put("correlationId", "afc-corr-list-prod-0001");
    @SuppressWarnings("unchecked")
    Map<String, Object> extensions = new LinkedHashMap<>((Map<String, Object>) body.get("extensions"));
    extensions.put(
        "financialList",
        Map.of(
            "companyId",
            COMPANY,
            "originSystem",
            "ACTIONHUB_PAY",
            "environment",
            "PRODUCTION",
            "limit",
            2));
    body.put("extensions", extensions);
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("READY")
        .jsonPath("$.capabilityId")
        .isEqualTo("LIST_PAYMENT_TRANSACTIONS")
        .jsonPath("$.resultSummary.environment")
        .isEqualTo("PRODUCTION")
        .jsonPath("$.resultSummary.reviewCount")
        .isEqualTo(9);
    verify(provider)
        .execute(
            argThat(
                request ->
                    "LIST_PAYMENT_TRANSACTIONS".equals(request.capabilityId())
                        && "homolog-padaria".equals(request.capabilityInputs().get("payAppId"))
                        && "PRODUCTION".equals(request.capabilityInputs().get("environment"))));
  }

  @Test
  void unknownListEnvironmentReproducesInvalidPayloadWithoutOpeningForeignBinding() {
    Map<String, Object> body = listEnvelope(COMPANY, true);
    body.put("idempotencyKey", "list:" + COMPANY + ":LIVE");
    body.put("correlationId", "afc-corr-list-live-0001");
    @SuppressWarnings("unchecked")
    Map<String, Object> extensions = new LinkedHashMap<>((Map<String, Object>) body.get("extensions"));
    extensions.put(
        "financialList",
        Map.of(
            "companyId",
            COMPANY,
            "originSystem",
            "ACTIONHUB_PAY",
            "environment",
            "LIVE",
            "limit",
            2));
    body.put("extensions", extensions);
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
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
  void financeActionListPersistsInMonitorAndRepeatedSyncDoesNotDuplicate() {
    when(provider.execute(any()))
        .thenReturn(Mono.just(listResultWithItem("pay-persist-77", "PENDING")))
        .thenReturn(Mono.just(listResultWithItem("pay-persist-77", "PAID")));
    String runId = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
    postList("list-" + runId + "-1", "afp-" + runId + "-1", "list-persist-1");
    postList("list-" + runId + "-2", "afp-" + runId + "-2", "list-persist-2");
    String syncId = "sync:" + COMPANY + ":HOMOLOG:" + runId;
    String interactionId = "int:actionfinance:list-" + runId + "-1";
    String paymentId = "pay:" + COMPANY + ":pay-persist-77";
    @SuppressWarnings("unchecked")
    Map<String, Object> body =
        client
            .get()
            .uri("/v1/console/monitor/records?q={q}&limit=50", COMPANY)
            .header("X-Spider-Credential-Ref", "local-demo-console")
            .exchange()
            .expectStatus()
            .isOk()
            .expectBody(Map.class)
            .returnResult()
            .getResponseBody();
    assertEquals(false, body.get("durable"));
    assertEquals("P90D", body.get("retention"));
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> items = (List<Map<String, Object>>) body.get("items");
    List<Map<String, Object>> syncs =
        items.stream().filter(item -> syncId.equals(item.get("recordId"))).toList();
    List<Map<String, Object>> interactions =
        items.stream().filter(item -> String.valueOf(item.get("recordId")).startsWith("int:actionfinance:list-" + runId)).toList();
    List<Map<String, Object>> payments =
        items.stream().filter(item -> paymentId.equals(item.get("recordId"))).toList();
    assertEquals(1, syncs.size());
    assertEquals(2, interactions.size());
    assertEquals(1, payments.size());
    assertEquals("COMPLETED", syncs.getFirst().get("technicalState"));
    assertEquals("SYNC_EXECUTION", syncs.getFirst().get("kind"));
    assertEquals("SATELLITE_INTERACTION", interactions.getFirst().get("kind"));
    assertEquals("DISCOVERED_PAYMENT", payments.getFirst().get("kind"));
    assertEquals("actionhub-pay", payments.getFirst().get("origin"));
    assertEquals("PAID", payments.getFirst().get("financialState"));
    assertNull(payments.getFirst().get("executionId"));
    assertNull(interactions.getFirst().get("executionId"));
    client
        .get()
        .uri("/v1/console/monitor/records/{id}", syncId)
        .header("X-Spider-Credential-Ref", "local-demo-console")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.recordId")
        .isEqualTo(syncId)
        .jsonPath("$.kind")
        .isEqualTo("SYNC_EXECUTION")
        .jsonPath("$.executionId")
        .isEmpty();
  }

  @Test
  void disallowedCompanyAttributeClosesJourneyAfterAuthLikeSandboxIncident() {
    String messageId = "afm-45f062cf-4076-4403-ae06-fa6cfc2e57bb";
    String correlationId = "afp-42e5b0dc-6241-41ac-b603-564de9e5a53f-1";
    String loja = "624023a4-57e3-415c-b7d0-925ca1acd3b7";
    Map<String, Object> body = listEnvelope(COMPANY, true);
    body.put("messageId", messageId);
    body.put("correlationId", correlationId);
    body.put("idempotencyKey", "list-incident-afm-45");
    @SuppressWarnings("unchecked")
    Map<String, Object> context = new LinkedHashMap<>((Map<String, Object>) body.get("context"));
    @SuppressWarnings("unchecked")
    Map<String, Object> snapshot = new LinkedHashMap<>((Map<String, Object>) context.get("snapshot"));
    @SuppressWarnings("unchecked")
    Map<String, Object> attributes = new LinkedHashMap<>((Map<String, Object>) snapshot.get("attributes"));
    attributes.put("companyId", loja);
    snapshot.put("attributes", attributes);
    context.put("snapshot", snapshot);
    body.put("context", context);
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
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
    String interactionId = "int:actionfinance:" + messageId;
    client
        .get()
        .uri("/v1/console/monitor/records/{id}", interactionId)
        .header("X-Spider-Credential-Ref", "local-demo-console")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.recordId")
        .isEqualTo(interactionId)
        .jsonPath("$.technicalState")
        .isEqualTo("REJECTED")
        .jsonPath("$.relatedSyncId")
        .isEqualTo("sync:" + COMPANY + ":HOMOLOG:42e5b0dc-6241-41ac-b603-564de9e5a53f")
        .jsonPath("$.journeyAvailability")
        .isEqualTo("COMPLETE")
        .jsonPath("$.journeyStages[?(@.stageId=='received')].state")
        .value(states -> assertEquals("completed", ((List<?>) states).getFirst()))
        .jsonPath("$.journeyStages[?(@.stageId=='authenticated')].state")
        .value(states -> assertEquals("completed", ((List<?>) states).getFirst()))
        .jsonPath("$.journeyStages[?(@.stageId=='contract_validated')].state")
        .value(states -> assertEquals("rejected", ((List<?>) states).getFirst()))
        .jsonPath("$.journeyStages[?(@.stageId=='contract_validated')].title")
        .value(titles -> assertEquals("Validação do contrato e contexto", ((List<?>) titles).getFirst()))
        .jsonPath("$.journeyStages[?(@.stageId=='capability_resolved')].state")
        .value(states -> assertEquals("not_reached", ((List<?>) states).getFirst()))
        .jsonPath("$.journeyStages[?(@.stageId=='context_ai')].state")
        .value(states -> assertEquals("not_used", ((List<?>) states).getFirst()))
        .jsonPath("$.journeyStages[?(@.stageId=='response_produced')].state")
        .value(states -> assertEquals("rejected", ((List<?>) states).getFirst()));
  }

  @Test
  void emptyPayListCompletesInteractionAndSyncWithZeroCounts() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-empty",
                    "actionhub-pay",
                    null,
                    "ACTIONHUB_PAY",
                    SatelliteContractV1.WATERMARK_FINANCIAL,
                    List.of(),
                    List.of(),
                    Map.of("kind", "EXTERNAL_PAYMENT_LIST", "itemCount", 0, "environment", "HOMOLOG", "origin", "ACTIONHUB_PAY"))));
    String runId = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
    Map<String, Object> body = listEnvelope(COMPANY, true);
    body.put("messageId", "list-" + runId + "-1");
    body.put("correlationId", "afp-" + runId + "-1");
    body.put("idempotencyKey", "list-empty-" + runId);
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("READY");
    String syncId = "sync:" + COMPANY + ":HOMOLOG:" + runId;
    client
        .get()
        .uri("/v1/console/monitor/records/{id}", syncId)
        .header("X-Spider-Credential-Ref", "local-demo-console")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.technicalState")
        .isEqualTo("COMPLETED")
        .jsonPath("$.foundCount")
        .isEqualTo(0)
        .jsonPath("$.newCount")
        .isEqualTo(0)
        .jsonPath("$.journeyAvailability")
        .isEqualTo("COMPLETE")
        .jsonPath("$.relatedInteractionId")
        .isEqualTo("int:actionfinance:list-" + runId + "-1");
  }

  @Test
  void providerUnavailableClosesAsUnavailable() {
    when(provider.execute(any())).thenReturn(Mono.just(ExecutionResult.unavailable()));
    Map<String, Object> body = listEnvelope(COMPANY, true);
    body.put("messageId", "afm-unavail-list-0001");
    body.put("correlationId", "afc-unavail-list-0001");
    body.put("idempotencyKey", "list-unavail-0001");
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("PROVIDER_UNAVAILABLE");
    client
        .get()
        .uri("/v1/console/monitor/records/{id}", "int:actionfinance:afm-unavail-list-0001")
        .header("X-Spider-Credential-Ref", "local-demo-console")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.technicalState")
        .isEqualTo("UNAVAILABLE")
        .jsonPath("$.journeyStages[?(@.stageId=='response_produced')].state")
        .value(states -> assertEquals("failed", ((List<?>) states).getFirst()));
  }

  @Test
  void uncertainTimeoutClosesAsUnknownEffect() {
    when(provider.execute(any())).thenReturn(Mono.just(ExecutionResult.unknownEffect()));
    Map<String, Object> body = listEnvelope(COMPANY, true);
    body.put("messageId", "afm-timeout-list-0001");
    body.put("correlationId", "afc-timeout-list-0001");
    body.put("idempotencyKey", "list-timeout-0001");
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("UNKNOWN_EFFECT");
    client
        .get()
        .uri("/v1/console/monitor/records/{id}", "int:actionfinance:afm-timeout-list-0001")
        .header("X-Spider-Credential-Ref", "local-demo-console")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.technicalState")
        .isEqualTo("UNKNOWN_EFFECT");
  }

  @Test
  void schemaInvalidEnvelopeIsRejectedBeforeService() {
    Map<String, Object> body = listEnvelope(COMPANY, true);
    body.put("contractVersion", "0.9");
    body.put("messageId", "afm-bad-contract-0001");
    body.put("correlationId", "afc-bad-contract-0001");
    body.put("idempotencyKey", "list-bad-contract-0001");
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isBadRequest()
        .expectBody()
        .jsonPath("$.errorCode")
        .isEqualTo("INVALID_PAYLOAD");
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

  private void postList(String messageId, String correlationId, String idempotencyKey) {
    Map<String, Object> body = listEnvelope(COMPANY, true);
    body.put("messageId", messageId);
    body.put("correlationId", correlationId);
    body.put("idempotencyKey", idempotencyKey);
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isOk();
  }

  private static ExecutionResult listResultWithItem(String transactionId, String status) {
    return new ExecutionResult(
        true,
        "COMPLETED",
        "preq-persist",
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
            1,
            "environment",
            "HOMOLOG",
            "origin",
            "ACTIONHUB_PAY",
            "companyId",
            COMPANY,
            "items",
            List.of(
                Map.of(
                    "transactionId",
                    transactionId,
                    "normalizedStatus",
                    status,
                    "originalStatus",
                    status))));
  }

  @Test
  void contract16PublishesExplicitPayerAnd14StaysWithoutThoseKeys() {
    when(provider.execute(any()))
        .thenAnswer(
            invocation -> {
              ExecutionRequest request = invocation.getArgument(0);
              boolean explicit = "1.6".equals(
                  request.quoteInputs() == null ? null : request.quoteInputs().get("satelliteContractVersion"));
              return Mono.just(listResult(explicit ? explicitQuote() : legacyQuote()));
            });
    Logger logger = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
    ListAppender<ILoggingEvent> logs = new ListAppender<>();
    logs.start();
    logger.addAppender(logs);
    try {
      client
          .post()
          .uri("/v1/satellites/interactions")
          .header("X-Spider-Satellite-Id", "actionfinance")
          .header("X-Spider-Satellite-Secret", SECRET)
          .contentType(MediaType.APPLICATION_JSON)
          .bodyValue(listEnvelopeVersion("1.6", "list-16-explicit"))
          .exchange()
          .expectStatus()
          .isOk()
          .expectBody()
          .jsonPath("$.contractVersion")
          .isEqualTo("1.6")
          .jsonPath("$.spiderPath")
          .isEqualTo(SatelliteContractV1.PATH_V1_6)
          .jsonPath("$.states")
          .doesNotExist()
          .jsonPath("$.resultSummary.items[0].payerName")
          .isEqualTo("NomeSecreto149")
          .jsonPath("$.resultSummary.items[0].payerEmail")
          .isEqualTo("secreto149@example.test")
          .jsonPath("$.resultSummary.items[0].payerLabel")
          .isEqualTo("tecnico@amount.hub.local")
          .jsonPath("$.resultSummary.items[0].processorInstallments")
          .isEqualTo(1)
          .jsonPath("$.resultSummary.items[0].processorApprovedAt")
          .isEqualTo("2026-10-30T18:58:54.000Z");
      client
          .post()
          .uri("/v1/satellites/interactions")
          .header("X-Spider-Satellite-Id", "actionfinance")
          .header("X-Spider-Satellite-Secret", SECRET)
          .contentType(MediaType.APPLICATION_JSON)
          .bodyValue(listEnvelopeVersion("1.4", "list-14-same-pay"))
          .exchange()
          .expectStatus()
          .isOk()
          .expectBody()
          .jsonPath("$.contractVersion")
          .isEqualTo("1.4")
          .jsonPath("$.spiderPath")
          .isEqualTo(SatelliteContractV1.PATH_V1_4)
          .jsonPath("$.resultSummary.items[0].payerLabel")
          .isEqualTo("tecnico@amount.hub.local")
          .jsonPath("$.resultSummary.items[0].payerName")
          .doesNotExist()
          .jsonPath("$.resultSummary.items[0].payerEmail")
          .doesNotExist()
          .jsonPath("$.resultSummary.items[0].storeOrderReference")
          .doesNotExist();
    } finally {
      logger.detachAppender(logs);
    }
    String written =
        logs.list.stream().map(ILoggingEvent::getFormattedMessage).reduce("", (left, right) -> left + "\n" + right);
    assertFalse(written.contains("NomeSecreto149"));
    assertFalse(written.contains("secreto149@example.test"));
  }

  @Test
  void contract16RejectsAnotherCompanyBeforeProvider() {
    String other = "22222222-2222-4222-a222-222222222222";
    Map<String, Object> body = listEnvelope(other, false);
    body.put("contractVersion", "1.6");
    body.put("idempotencyKey", "list-16-foreign-company");
    body.put("messageId", "afm-list-16-foreign");
    body.put("correlationId", "afc-list-16-foreign");
    @SuppressWarnings("unchecked")
    Map<String, Object> context = new LinkedHashMap<>((Map<String, Object>) body.get("context"));
    @SuppressWarnings("unchecked")
    Map<String, Object> snapshot = new LinkedHashMap<>((Map<String, Object>) context.get("snapshot"));
    snapshot.put("schemaVersion", "1.6");
    context.put("snapshot", snapshot);
    body.put("context", context);
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

  private static ExecutionResult listResult(Map<String, Object> quote) {
    return new ExecutionResult(
        true,
        "COMPLETED",
        "preq-explicit",
        "actionhub-pay",
        null,
        "ACTIONHUB_PAY",
        SatelliteContractV1.WATERMARK_FINANCIAL,
        List.of(),
        List.of(),
        quote);
  }

  private static Map<String, Object> explicitQuote() {
    Map<String, Object> item = new LinkedHashMap<>();
    item.put("transactionId", "tx-explicit");
    item.put("payerKind", "EMAIL");
    item.put("payerLabel", "tecnico@amount.hub.local");
    item.put("payerName", "NomeSecreto149");
    item.put("payerEmail", "secreto149@example.test");
    item.put("storeOrderReference", "PED-149");
    item.put("processorPaymentId", "mp-149");
    item.put("processorApprovedAt", "2026-10-30T18:58:54.000Z");
    item.put("processorInstallments", 1);
    return quote(List.of(item));
  }

  private static Map<String, Object> legacyQuote() {
    return quote(List.of(Map.of(
        "transactionId", "tx-explicit",
        "payerKind", "EMAIL",
        "payerLabel", "tecnico@amount.hub.local")));
  }

  private static Map<String, Object> quote(List<?> items) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("kind", "EXTERNAL_PAYMENT_LIST");
    body.put("itemCount", items.size());
    body.put("environment", "HOMOLOG");
    body.put("origin", "ACTIONHUB_PAY");
    body.put("importPersisted", false);
    body.put("items", items);
    return body;
  }

  private static Map<String, Object> listEnvelopeVersion(String version, String idempotency) {
    Map<String, Object> body = listEnvelope(COMPANY, true);
    body.put("contractVersion", version);
    body.put("idempotencyKey", idempotency);
    body.put("messageId", "afm-" + idempotency);
    body.put("correlationId", "afc-" + idempotency);
    @SuppressWarnings("unchecked")
    Map<String, Object> context = new LinkedHashMap<>((Map<String, Object>) body.get("context"));
    @SuppressWarnings("unchecked")
    Map<String, Object> snapshot = new LinkedHashMap<>((Map<String, Object>) context.get("snapshot"));
    snapshot.put("schemaVersion", version);
    context.put("snapshot", snapshot);
    body.put("context", context);
    return body;
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

  @Test
  @SuppressWarnings("unchecked")
  void publishedListContractFixtureIsAcceptedWhenCompanyIsAllowlisted() throws Exception {
    Map<String, Object> body = loadContract("contracts/actionfinance-list-external-payments-1.4.valid.json");
    replaceCompany(body, "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c", COMPANY);
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-contract",
                    "actionhub-pay",
                    null,
                    "ACTIONHUB_PAY",
                    SatelliteContractV1.WATERMARK_FINANCIAL,
                    List.of(),
                    List.of(),
                    Map.of("kind", "EXTERNAL_PAYMENT_LIST", "itemCount", 0, "environment", "HOMOLOG"))));
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
        .header("X-Spider-Satellite-Secret", SECRET)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(body)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.capabilityId")
        .isEqualTo("LIST_PAYMENT_TRANSACTIONS");
    verify(provider).execute(any());
  }

  @Test
  void publishedListContractRejectsProductionLojaCompanyWithoutCallingProvider() throws Exception {
    Map<String, Object> body = loadContract("contracts/actionfinance-list-external-payments-1.4.invalid-company.json");
    client
        .post()
        .uri("/v1/satellites/interactions")
        .header("X-Spider-Satellite-Id", "actionfinance")
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

  @SuppressWarnings("unchecked")
  private static Map<String, Object> loadContract(String resource) throws Exception {
    try (var in = ActionFinanceSatelliteInteractionHttpTest.class.getClassLoader().getResourceAsStream(resource)) {
      return new com.fasterxml.jackson.databind.ObjectMapper().readValue(in, Map.class);
    }
  }

  @SuppressWarnings("unchecked")
  private static void replaceCompany(Map<String, Object> node, String from, String to) {
    if (node == null) {
      return;
    }
    for (Map.Entry<String, Object> entry : node.entrySet()) {
      if (from.equals(entry.getValue())) {
        entry.setValue(to);
      } else if (entry.getValue() instanceof Map<?, ?> nested) {
        replaceCompany((Map<String, Object>) nested, from, to);
      }
    }
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
