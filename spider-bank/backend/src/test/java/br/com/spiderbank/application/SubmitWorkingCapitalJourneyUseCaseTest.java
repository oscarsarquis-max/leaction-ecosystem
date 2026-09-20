package br.com.spiderbank.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class SubmitWorkingCapitalJourneyUseCaseTest {

  @Test
  void unconfirmedObjectiveNeverCallsSpider() {
    RecordingGateway gateway = new RecordingGateway(SpiderDecisionGateway.Result.ok(sampleBody("corr-ok-1")));
    SubmitWorkingCapitalJourneyUseCase useCase =
        new SubmitWorkingCapitalJourneyUseCase(gateway, new InMemoryJourneyStore());
    CreditJourneyException error =
        assertThrows(CreditJourneyException.class, () -> useCase.execute(false, "corr-ok-1", "idem-ok-1"));
    assertEquals("OBJECTIVE_NOT_CONFIRMED", error.errorCode());
    assertEquals(0, gateway.calls.get());
  }

  @Test
  void spiderImpedimentsAreProjectedWithoutFabricatingCredit() {
    SubmitWorkingCapitalJourneyUseCase useCase =
        new SubmitWorkingCapitalJourneyUseCase(
            command -> SpiderDecisionGateway.Result.ok(sampleBody(command.correlationId())),
            new InMemoryJourneyStore());
    Map<String, Object> view = useCase.execute(true, "corr-ok-2", "idem-ok-2");
    assertEquals("ANALYSIS_BLOCKED", view.get("status"));
    assertEquals("NONE", view.get("creditDecision"));
    assertEquals(false, view.get("analysisComplete"));
    assertTrue(String.valueOf(view.get("explanation")).contains("não é recusa de crédito"));
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> impediments = (List<Map<String, Object>>) view.get("impediments");
    assertEquals(7, impediments.size());
    assertEquals("Identificar o cliente autenticado", impediments.get(0).get("title"));
  }

  @Test
  void sameIdempotencyKeyReplaysWithoutSecondCall() {
    RecordingGateway gateway = new RecordingGateway(SpiderDecisionGateway.Result.ok(sampleBody("corr-ok-3")));
    SubmitWorkingCapitalJourneyUseCase useCase =
        new SubmitWorkingCapitalJourneyUseCase(gateway, new InMemoryJourneyStore());
    Map<String, Object> first = useCase.execute(true, "corr-ok-3", "idem-replay");
    Map<String, Object> second = useCase.execute(true, "corr-ok-3", "idem-replay");
    assertEquals(first.get("decisionId"), second.get("decisionId"));
    assertEquals(1, gateway.calls.get());
  }

  @Test
  void divergentCorrelationIsIntegrationFailure() {
    SubmitWorkingCapitalJourneyUseCase useCase =
        new SubmitWorkingCapitalJourneyUseCase(
            command -> SpiderDecisionGateway.Result.ok(sampleBody("other-correlation")),
            new InMemoryJourneyStore());
    CreditJourneyException error =
        assertThrows(CreditJourneyException.class, () -> useCase.execute(true, "corr-ok-4", "idem-corr"));
    assertEquals("INTEGRATION_FAILURE", error.errorCode());
    assertEquals(502, error.status());
  }

  @Test
  void spiderUnavailableIsRetryableAndNotACreditRefusal() {
    SubmitWorkingCapitalJourneyUseCase useCase =
        new SubmitWorkingCapitalJourneyUseCase(
            command -> SpiderDecisionGateway.Result.spiderUnavailable(), new InMemoryJourneyStore());
    CreditJourneyException error =
        assertThrows(CreditJourneyException.class, () -> useCase.execute(true, "corr-ok-5", "idem-down"));
    assertEquals("SPIDER_UNAVAILABLE", error.errorCode());
    assertTrue(error.retryable());
    assertFalse(error.getMessage().toLowerCase().contains("recusa") && error.getMessage().contains("aprov"));
    assertTrue(error.getMessage().contains("não é recusa de crédito"));
  }

  @Test
  void invalidDeclaredAmountIsRejectedBeforeSpider() {
    RecordingGateway gateway = new RecordingGateway(SpiderDecisionGateway.Result.ok(sampleBody("corr-ok-7")));
    SubmitWorkingCapitalJourneyUseCase useCase =
        new SubmitWorkingCapitalJourneyUseCase(gateway, new InMemoryJourneyStore());
    CreditJourneyException error =
        assertThrows(
            CreditJourneyException.class,
            () -> useCase.execute(true, "corr-ok-7", "idem-invalid", "token", -1L, 12));
    assertEquals("VALIDATION_ERROR", error.errorCode());
    assertEquals(0, gateway.calls.get());
  }

  @Test
  void confirmedJourneyTransportsAssertionAndDeclaredParametersWithoutChoosingThePlan() {
    RecordingGateway gateway = new RecordingGateway(SpiderDecisionGateway.Result.ok(sampleBody("corr-ok-6")));
    SubmitWorkingCapitalJourneyUseCase useCase =
        new SubmitWorkingCapitalJourneyUseCase(gateway, new InMemoryJourneyStore());
    useCase.execute(true, "corr-ok-6", "idem-params", "v1.spiderbank.cust-demo-ok.1.2.abc", 1_000_000L, 12);
    assertEquals(1, gateway.calls.get());
    assertEquals("v1.spiderbank.cust-demo-ok.1.2.abc", gateway.last.extensions().get("customerAssertion"));
    @SuppressWarnings("unchecked")
    Map<String, Object> parameters = (Map<String, Object>) gateway.last.extensions().get("workingCapitalParameters");
    assertEquals(1_000_000L, parameters.get("principalCents"));
    assertEquals(12, parameters.get("termMonths"));
    assertEquals("USER_DECLARED", parameters.get("origin"));
  }

  @Test
  void envelopeNeverChoosesThePlan() {
    Map<String, Object> envelope =
        SatelliteEnvelopeFactory.build(
            new SpiderDecisionGateway.Command(
                "corr-env-1",
                "idem-env-1",
                "msg-env-1",
                "2026-09-18T15:00:00Z",
                GovernedCreditContext.attributes()));
    assertEquals("WORKING_CAPITAL_ASSESSMENT", envelope.get("purpose"));
    assertEquals("spiderbank", envelope.get("satelliteId"));
    @SuppressWarnings("unchecked")
    Map<String, Object> objective = (Map<String, Object>) envelope.get("objective");
    assertEquals("SEEK_WORKING_CAPITAL", objective.get("text"));
    assertEquals("USER_DECLARED", objective.get("origin"));
    assertFalse(envelope.containsKey("intent"));
    assertFalse(envelope.containsKey("planId"));
  }

  private static Map<String, Object> sampleBody(String correlationId) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contractVersion", "1.0");
    body.put("status", "PLAN_IMPEDED");
    body.put("decisionId", "spd-test");
    body.put("correlationId", correlationId);
    body.put("contextRef", "ctx-test");
    body.put("requiredAction", "PRESENT_PLAN_IMPEDIMENTS");
    body.put(
        "explanation",
        "A Spider mapeou a declaração reconhecida para SEEK_WORKING_CAPITAL e selecionou o plano WORKING_CAPITAL_DIAGNOSTIC_V1. Isso não é recusa de crédito.");
    body.put("watermark", "DEMONSTRAÇÃO — DADOS SINTÉTICOS — NÃO É ANÁLISE DE CRÉDITO NEM OFERTA");
    body.put(
        "resultSummary",
        Map.of(
            "intent",
            "SEEK_WORKING_CAPITAL",
            "planId",
            "WORKING_CAPITAL_DIAGNOSTIC_V1",
            "analysisComplete",
            false,
            "providerDispatched",
            false,
            "impediments",
            List.of(
                Map.of("sequence", 1, "capabilityId", "IDENTIFY_CUSTOMER", "availability", "AVAILABLE", "reason", "sem cliente"),
                Map.of("sequence", 2, "capabilityId", "GET_CUSTOMER_PROFILE", "availability", "NOT_AVAILABLE", "reason", "indisponível"),
                Map.of("sequence", 3, "capabilityId", "CHECK_CUSTOMER_REGISTRATION", "availability", "NOT_AVAILABLE", "reason", "indisponível"),
                Map.of("sequence", 4, "capabilityId", "GET_CREDIT_PROFILE", "availability", "NOT_AVAILABLE", "reason", "indisponível"),
                Map.of("sequence", 5, "capabilityId", "FIND_ELIGIBLE_PRODUCTS", "availability", "NOT_AVAILABLE", "reason", "indisponível"),
                Map.of("sequence", 6, "capabilityId", "SIMULATE_WORKING_CAPITAL", "availability", "NOT_AVAILABLE", "reason", "indisponível"),
                Map.of("sequence", 7, "capabilityId", "PRESENT_OPTIONS", "availability", "NOT_AVAILABLE", "reason", "indisponível"))));
    return body;
  }

  private static final class RecordingGateway implements SpiderDecisionGateway {
    private final Result result;
    private final AtomicInteger calls = new AtomicInteger();
    private Command last;

    private RecordingGateway(Result result) {
      this.result = result;
    }

    @Override
    public Result submit(Command command) {
      last = command;
      calls.incrementAndGet();
      return result;
    }
  }
}
