package br.com.banco.spider.satellite.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.banco.spider.config.CreditDemoProperties;
import br.com.banco.spider.config.SatelliteContractProperties;
import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.satellite.SatelliteContractV1Test;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextBlock;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Objective;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;

class WorkingCapitalDiagnosticExecutorTest {

  private static final String SECRET = "test-assertion-secret";

  @Test
  void skipsWithoutValidAssertionAndNeverCallsTheProvider() {
    ProviderCapabilityPort providers = mock(ProviderCapabilityPort.class);
    WorkingCapitalDiagnosticExecutor executor = executor(providers, true);
    WorkingCapitalDiagnosticExecutor.Attempt attempt = executor.tryExecute(request(Map.of()), "ctx-1").block();
    assertFalse(attempt.handled());
    verify(providers, never()).execute(any());
  }

  @Test
  void executesSevenStepsAndComposesOnlyReceivedResults() {
    ProviderCapabilityPort providers = stubProvider(Map.of());
    WorkingCapitalDiagnosticExecutor executor = executor(providers, true);
    SatelliteInteractionService.Outcome outcome =
        executor.tryExecute(request(extensions("cust-demo-ok", 1_000_000L, 12)), "ctx-ok").block().outcome();
    assertEquals("READY", outcome.body().get("status"));
    @SuppressWarnings("unchecked")
    Map<String, Object> summary = (Map<String, Object>) outcome.body().get("resultSummary");
    assertEquals(true, summary.get("simulationComplete"));
    assertEquals(false, summary.get("analysisComplete"));
    assertEquals("NONE", summary.get("creditDecision"));
    assertEquals(false, summary.get("offerable"));
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> steps = (List<Map<String, Object>>) summary.get("steps");
    assertEquals(7, steps.size());
    assertEquals("IDENTIFY_CUSTOMER", steps.get(0).get("capabilityId"));
    assertEquals(true, steps.get(0).get("completed"));
    assertEquals("PRESENT_OPTIONS", steps.get(6).get("capabilityId"));
    @SuppressWarnings("unchecked")
    Map<String, Object> options = (Map<String, Object>) summary.get("options");
    assertEquals(1_120_000, ((Map<?, ?>) options.get("simulation")).get("totalCents"));
    verify(providers, times(5)).execute(any());
  }

  @Test
  void pendingRegistrationStopsBeforeSimulation() {
    ProviderCapabilityPort providers = stubProvider(Map.of());
    WorkingCapitalDiagnosticExecutor executor = executor(providers, true);
    SatelliteInteractionService.Outcome outcome =
        executor
            .tryExecute(request(extensions("cust-demo-pending-registration", 1_000_000L, 12)), "ctx-pending")
            .block()
            .outcome();
    assertEquals("MISSING_CONTEXT", outcome.body().get("status"));
    verify(providers, times(2)).execute(any());
  }

  @Test
  void missingAmountAsksForSpecificComplementWithoutDispatch() {
    ProviderCapabilityPort providers = mock(ProviderCapabilityPort.class);
    WorkingCapitalDiagnosticExecutor executor = executor(providers, true);
    Instant now = Instant.now();
    Map<String, Object> extensions = new LinkedHashMap<>();
    extensions.put(
        "customerAssertion",
        DemoCustomerAssertion.issue(SECRET, "spiderbank", "cust-demo-ok", now, now.plusSeconds(600)));
    SatelliteInteractionService.Outcome outcome = executor.tryExecute(request(extensions), "ctx-missing").block().outcome();
    assertEquals("MISSING_CONTEXT", outcome.body().get("status"));
    assertEquals(List.of("principalCents", "termMonths"), outcome.body().get("missingContext"));
    verify(providers, never()).execute(any());
  }

  @Test
  void missingCapabilityRouteImpedesEvenIfTheMockCouldBeOnline() {
    ProviderCapabilityPort providers = mock(ProviderCapabilityPort.class);
    SatelliteRegistry registry = new SatelliteRegistry(SatelliteContractV1Test.properties());
    CreditDemoProperties demo = new CreditDemoProperties();
    demo.setEnabled(true);
    demo.setAssertionSecret(SECRET);
    WorkingCapitalDiagnosticExecutor executor = new WorkingCapitalDiagnosticExecutor(registry, providers, demo, null);
    SatelliteInteractionService.Outcome outcome =
        executor.tryExecute(request(extensions("cust-demo-ok", 1_000_000L, 12)), "ctx-route").block().outcome();
    assertEquals("PLAN_IMPEDED", outcome.body().get("status"));
    verify(providers, never()).execute(any());
  }

  private static WorkingCapitalDiagnosticExecutor executor(ProviderCapabilityPort providers, boolean enabled) {
    CreditDemoProperties demo = new CreditDemoProperties();
    demo.setEnabled(enabled);
    demo.setAssertionSecret(SECRET);
    return new WorkingCapitalDiagnosticExecutor(new SatelliteRegistry(creditProperties()), providers, demo, null);
  }

  private static SatelliteContractProperties creditProperties() {
    SatelliteContractProperties properties = SatelliteContractV1Test.properties();
    ProviderEntry credit = new ProviderEntry();
    credit.setRole("PROVIDER");
    credit.setStatus("TEST_DOUBLE");
    credit.setCapabilities(
        List.of(
            "GET_CUSTOMER_PROFILE",
            "CHECK_CUSTOMER_REGISTRATION",
            "GET_CREDIT_PROFILE",
            "FIND_ELIGIBLE_PRODUCTS",
            "SIMULATE_WORKING_CAPITAL"));
    credit.setSecret("credit-test-only");
    properties.getProviders().put("credit-provider-mock", credit);
    return properties;
  }

  private static ProviderCapabilityPort stubProvider(Map<String, ExecutionResult> overrides) {
    ProviderCapabilityPort providers = mock(ProviderCapabilityPort.class);
    when(providers.execute(any()))
        .thenAnswer(
            invocation -> {
              ExecutionRequest request = invocation.getArgument(0);
              if (overrides.containsKey(request.capabilityId())) {
                return Mono.just(overrides.get(request.capabilityId()));
              }
              return Mono.just(completed(request));
            });
    return providers;
  }

  private static ExecutionResult completed(ExecutionRequest request) {
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("testDouble", true);
    result.put("offerable", false);
    result.put("origin", "NON_BINDING_DEMO");
    if ("FIND_ELIGIBLE_PRODUCTS".equals(request.capabilityId())) {
      if ("INELIGIBLE".equals(request.capabilityInputs().get("scenarioKey"))) {
        result.put("products", List.of());
        return quoted(request, "REJECTED", result);
      }
      result.put(
          "products",
          List.of(Map.of("productCode", "WC_SYNTHETIC_TEST_1", "title", "Capital de giro sintético de teste", "offerable", false)));
    }
    if ("SIMULATE_WORKING_CAPITAL".equals(request.capabilityId())) {
      result.put("totalCents", 1_120_000);
      result.put("interestCents", 120_000);
      result.put("principalCents", 1_000_000);
      result.put("termMonths", 12);
    }
    if ("CHECK_CUSTOMER_REGISTRATION".equals(request.capabilityId())
        && "PENDING_REGISTRATION".equals(request.capabilityInputs().get("scenarioKey"))) {
      result.put("missingFields", List.of("syntheticRegistrationComplete"));
      return quoted(request, "PENDING", result, List.of("MISSING_CONTEXT"));
    }
    if ("GET_CUSTOMER_PROFILE".equals(request.capabilityId())
        && "NO_PROFILE".equals(request.capabilityInputs().get("scenarioKey"))) {
      return quoted(request, "PENDING", result, List.of("MISSING_CONTEXT"));
    }
    if ("GET_CREDIT_PROFILE".equals(request.capabilityId())
        && "REJECTED".equals(request.capabilityInputs().get("scenarioKey"))) {
      return quoted(request, "REJECTED", result, List.of("SYNTHETIC_SCENARIO_REJECTED"));
    }
    if ("GET_CREDIT_PROFILE".equals(request.capabilityId())
        && "HUMAN_REVIEW".equals(request.capabilityInputs().get("scenarioKey"))) {
      return quoted(request, "PENDING", result, List.of("SYNTHETIC_HUMAN_REVIEW"));
    }
    return quoted(request, "COMPLETED", result);
  }

  private static ExecutionResult quoted(ExecutionRequest request, String status, Map<String, Object> result) {
    return quoted(request, status, result, List.of());
  }

  private static ExecutionResult quoted(
      ExecutionRequest request, String status, Map<String, Object> result, List<String> reasons) {
    Map<String, Object> quote = new LinkedHashMap<>();
    quote.put("kind", "CREDIT_STEP_RESULT");
    quote.put("capabilityId", request.capabilityId());
    quote.put("executorStatus", status);
    quote.put("reasonCodes", reasons);
    quote.put("result", result);
    return new ExecutionResult(
        true, status, request.requestId(), "credit-provider-mock", "pref", "NON_BINDING_DEMO", "wm", List.of(), List.of(), quote);
  }

  private static Map<String, Object> extensions(String subject, long cents, int months) {
    Instant now = Instant.now();
    Map<String, Object> extensions = new LinkedHashMap<>();
    extensions.put("customerAssertion", DemoCustomerAssertion.issue(SECRET, "spiderbank", subject, now, now.plusSeconds(600)));
    extensions.put("workingCapitalParameters", Map.of("principalCents", cents, "termMonths", months, "origin", "USER_DECLARED"));
    return extensions;
  }

  private static SatelliteInteractionRequest request(Map<String, Object> extensions) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", "SPIDERBANK_PUBLIC_DEMO");
    attributes.put("theme", "working_capital");
    return new SatelliteInteractionRequest(
        "1.0",
        "msg-exec-1",
        "11111111-1111-1111-1111-111111111111",
        "spiderbank",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-18T15:00:00Z",
        "idem-exec-1",
        SatelliteContractV1.PURPOSE_WORKING_CAPITAL,
        new Objective(SatelliteContractV1.SEEK_WORKING_CAPITAL, "USER_DECLARED", "2026-09-18T15:00:00Z"),
        new ContextBlock(
            null,
            new ContextSnapshot(
                "1.0",
                "INTERNAL",
                true,
                new Provenance(
                    "SATELLITE_GOVERNED",
                    "SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1",
                    "2026-09-18T15:00:00Z",
                    "SERVER_REGISTRY",
                    "GOVERNED"),
                attributes)),
        "INTERNAL",
        "SYNC",
        Map.of(),
        extensions);
  }
}
