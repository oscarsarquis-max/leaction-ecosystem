package br.com.banco.spider.satellite.application;

import br.com.banco.spider.config.CreditDemoProperties;
import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import reactor.core.publisher.Mono;

public final class WorkingCapitalDiagnosticExecutor {

  private static final List<String> PROVIDER_STEPS =
      List.of(
          "GET_CUSTOMER_PROFILE",
          "CHECK_CUSTOMER_REGISTRATION",
          "GET_CREDIT_PROFILE",
          "FIND_ELIGIBLE_PRODUCTS",
          "SIMULATE_WORKING_CAPITAL");

  private final SatelliteRegistry registry;
  private final ProviderCapabilityPort providers;
  private final CreditDemoProperties creditDemo;
  private final OperationalEventPublisher events;

  public WorkingCapitalDiagnosticExecutor(
      SatelliteRegistry registry,
      ProviderCapabilityPort providers,
      CreditDemoProperties creditDemo,
      OperationalEventPublisher events) {
    this.registry = registry;
    this.providers = providers;
    this.creditDemo = creditDemo;
    this.events = events;
  }

  public Mono<Attempt> tryExecute(SatelliteInteractionRequest request, String contextRef) {
    if (creditDemo == null || !creditDemo.isEnabled()) {
      return Mono.just(Attempt.skip());
    }
    Object assertion = extension(request, "customerAssertion");
    DemoCustomerAssertion.Verified verified =
        assertion instanceof String token
            ? DemoCustomerAssertion.verify(creditDemo.getAssertionSecret(), request.satelliteId(), token)
            : null;
    if (verified == null) {
      return Mono.just(Attempt.skip());
    }
    Parameters parameters = parameters(request);
    if (parameters instanceof Parameters.Invalid invalid) {
      return Mono.just(
          Attempt.done(
              SatelliteInteractionService.Outcome.invalid(
                  400, invalid.code(), invalid.message(), request.correlationId())));
    }
    if (parameters instanceof Parameters.Missing missing) {
      return Mono.just(
          Attempt.done(
              response(
                  request,
                  contextRef,
                  "MISSING_CONTEXT",
                  "PROVIDE_CONTEXT",
                  "Informe valor e prazo declarados para a simulação demonstrativa. Eles não se tornam fatos de cadastro.",
                  missing.fields(),
                  projection(true, false, List.of(), null, verified.subjectRef(), null))));
    }
    Parameters.Present present = (Parameters.Present) parameters;
    String decisionId = "spd-" + UUID.randomUUID();
    List<Map<String, Object>> steps = new ArrayList<>();
    steps.add(identifyStep(verified.subjectRef()));
    return runProviderSteps(request, decisionId, verified.subjectRef(), present, 0, steps, new LinkedHashMap<>())
        .map(bundle -> Attempt.done(toOutcome(request, contextRef, decisionId, verified.subjectRef(), present, bundle)));
  }

  private Mono<Bundle> runProviderSteps(
      SatelliteInteractionRequest request,
      String decisionId,
      String subjectRef,
      Parameters.Present present,
      int index,
      List<Map<String, Object>> steps,
      Map<String, Map<String, Object>> results) {
    if (index >= PROVIDER_STEPS.size()) {
      steps.add(presentOptionsStep(results));
      return Mono.just(new Bundle("READY", "PRESENT_SIMULATION", List.of(), steps, results, true));
    }
    String capabilityId = PROVIDER_STEPS.get(index);
    if (registry.resolveProvider(capabilityId) == null) {
      steps.add(impeded(index + 2, capabilityId, "Capability ou rota ausente neste ambiente demonstrativo."));
      return Mono.just(
          new Bundle(
              "PLAN_IMPEDED",
              "PRESENT_PLAN_IMPEDIMENTS",
              List.of(),
              steps,
              results,
              false));
    }
    String scenarioKey = scenarioKey(subjectRef, capabilityId);
    Map<String, Object> inputs = new LinkedHashMap<>();
    if ("SIMULATE_WORKING_CAPITAL".equals(capabilityId)) {
      inputs.put("scenarioKey", scenarioKey);
      inputs.put("principalCents", present.principalCents());
      inputs.put("termMonths", present.termMonths());
    } else {
      inputs.put("scenarioKey", scenarioKey);
      inputs.put("subjectRef", subjectRef);
    }
    String requestId = "preq-" + UUID.randomUUID();
    emit(OperationalEventType.CAPABILITY_DISPATCHED, request, OperationalEventOutcome.INFO, capabilityId);
    return providers
        .execute(
            new ExecutionRequest(
                requestId,
                request.correlationId(),
                decisionId,
                capabilityId,
                "SIMULATE_WORKING_CAPITAL".equals(capabilityId)
                    ? "WORKING_CAPITAL_SIMULATION"
                    : SatelliteContractV1.PURPOSE_WORKING_CAPITAL,
                scenarioKey,
                "INTERNAL",
                Map.of(),
                inputs))
        .flatMap(
            result -> {
              emit(
                  OperationalEventType.PROVIDER_RESULT_RECEIVED,
                  request,
                  result.available() ? OperationalEventOutcome.SUCCESS : OperationalEventOutcome.FAILURE,
                  result.providerId());
              if (!result.available()) {
                steps.add(failed(index + 2, capabilityId, "Executor indisponível ou resposta inválida.", result));
                return Mono.just(
                    new Bundle(
                        "PROVIDER_UNAVAILABLE",
                        "RETRY_LATER",
                        List.of(),
                        steps,
                        results,
                        true));
              }
              Map<String, Object> quote = result.quote() == null ? Map.of() : result.quote();
              results.put(capabilityId, quote);
              String executorStatus = String.valueOf(quote.getOrDefault("executorStatus", result.status()));
              steps.add(executed(index + 2, capabilityId, executorStatus, result));
              if (!"COMPLETED".equals(executorStatus)) {
                return Mono.just(stop(executorStatus, quote, steps, results));
              }
              if ("FIND_ELIGIBLE_PRODUCTS".equals(capabilityId) && noEligible(quote)) {
                return Mono.just(
                    new Bundle(
                        "REJECTED",
                        "PRESENT_REJECTION",
                        List.of(),
                        steps,
                        results,
                        true));
              }
              return runProviderSteps(request, decisionId, subjectRef, present, index + 1, steps, results);
            });
  }

  private static Bundle stop(
      String executorStatus,
      Map<String, Object> quote,
      List<Map<String, Object>> steps,
      Map<String, Map<String, Object>> results) {
    Object reasons = quote.get("reasonCodes");
    boolean human = reasons != null && reasons.toString().contains("SYNTHETIC_HUMAN_REVIEW");
    boolean missing = reasons != null && reasons.toString().contains("MISSING_CONTEXT");
    if (human) {
      return new Bundle("PENDING", "PRESENT_SYNTHETIC_REVIEW", List.of(), steps, results, true);
    }
    if (missing) {
      return new Bundle("MISSING_CONTEXT", "PROVIDE_CONTEXT", List.of("syntheticSupportingContext"), steps, results, true);
    }
    return new Bundle("REJECTED", "PRESENT_REJECTION", List.of(), steps, results, true);
  }

  private SatelliteInteractionService.Outcome toOutcome(
      SatelliteInteractionRequest request,
      String contextRef,
      String decisionId,
      String subjectRef,
      Parameters.Present present,
      Bundle bundle) {
    Map<String, Object> summary =
        projection(
            true,
            bundle.providerDispatched(),
            bundle.steps(),
            bundle.results(),
            subjectRef,
            present);
    if ("READY".equals(bundle.status())) {
      summary.put("kind", "WORKING_CAPITAL_SIMULATION");
      summary.put("simulationComplete", true);
      summary.put("analysisComplete", false);
      summary.put("creditDecision", "NONE");
      summary.put("offerable", false);
      summary.put("testDouble", true);
      summary.put("boundary", "MOCK_ONLY");
      summary.put("options", presentOptions(bundle.results(), present));
    } else {
      summary.put("simulationComplete", false);
      summary.put("analysisComplete", false);
    }
    return response(
        request,
        contextRef,
        bundle.status(),
        bundle.requiredAction(),
        explanation(bundle),
        bundle.missing(),
        summary,
        decisionId);
  }

  private static Map<String, Object> presentOptions(
      Map<String, Map<String, Object>> results, Parameters.Present present) {
    Map<String, Object> options = new LinkedHashMap<>();
    options.put("principalCents", present.principalCents());
    options.put("termMonths", present.termMonths());
    options.put("origin", "USER_DECLARED");
    options.put("eligibleProducts", resultNode(results.get("FIND_ELIGIBLE_PRODUCTS"), "result"));
    options.put("simulation", resultNode(results.get("SIMULATE_WORKING_CAPITAL"), "result"));
    options.put("composedOnlyFromReceivedResults", true);
    return options;
  }

  @SuppressWarnings("unchecked")
  private static Object resultNode(Map<String, Object> step, String key) {
    if (step == null) {
      return null;
    }
    Object result = step.get(key);
    return result instanceof Map<?, ?> map ? new LinkedHashMap<>((Map<String, Object>) map) : result;
  }

  private static boolean noEligible(Map<String, Object> quote) {
    Object result = quote.get("result");
    if (result instanceof Map<?, ?> map) {
      Object products = map.get("products");
      return products instanceof List<?> list && list.isEmpty();
    }
    return false;
  }

  private static String scenarioKey(String subjectRef, String capabilityId) {
    return switch (subjectRef) {
      case "cust-demo-no-profile" -> "GET_CUSTOMER_PROFILE".equals(capabilityId) ? "NO_PROFILE" : "SUCCESS";
      case "cust-demo-pending-registration" ->
          "CHECK_CUSTOMER_REGISTRATION".equals(capabilityId) ? "PENDING_REGISTRATION" : "SUCCESS";
      case "cust-demo-ineligible" -> "FIND_ELIGIBLE_PRODUCTS".equals(capabilityId) ? "INELIGIBLE" : "SUCCESS";
      case "cust-demo-rejected" -> "GET_CREDIT_PROFILE".equals(capabilityId) ? "REJECTED" : "SUCCESS";
      case "cust-demo-review" -> "GET_CREDIT_PROFILE".equals(capabilityId) ? "HUMAN_REVIEW" : "SUCCESS";
      default -> "SUCCESS";
    };
  }

  private static Map<String, Object> identifyStep(String subjectRef) {
    Map<String, Object> row = new LinkedHashMap<>();
    row.put("sequence", 1);
    row.put("capabilityId", "IDENTIFY_CUSTOMER");
    row.put("availability", "AVAILABLE");
    row.put("completed", true);
    row.put("executor", "context-principal");
    row.put("subjectRef", subjectRef);
    row.put("reason", "Cliente sintético autenticado na sessão demonstrativa.");
    return row;
  }

  private static Map<String, Object> presentOptionsStep(Map<String, Map<String, Object>> results) {
    Map<String, Object> row = new LinkedHashMap<>();
    row.put("sequence", 7);
    row.put("capabilityId", "PRESENT_OPTIONS");
    row.put("availability", "AVAILABLE");
    row.put("completed", true);
    row.put("executor", "internal-composition");
    row.put("reason", "Composição exclusiva dos resultados recebidos.");
    row.put("usedSteps", List.of("FIND_ELIGIBLE_PRODUCTS", "SIMULATE_WORKING_CAPITAL"));
    return row;
  }

  private static Map<String, Object> executed(
      int sequence, String capabilityId, String executorStatus, ExecutionResult result) {
    Map<String, Object> row = new LinkedHashMap<>();
    row.put("sequence", sequence);
    row.put("capabilityId", capabilityId);
    row.put("availability", "AVAILABLE");
    row.put("completed", "COMPLETED".equals(executorStatus));
    row.put("executor", result.providerId());
    row.put("executorStatus", executorStatus);
    row.put("requestId", result.requestId());
    row.put("providerReference", result.providerReference());
    return row;
  }

  private static Map<String, Object> failed(int sequence, String capabilityId, String reason, ExecutionResult result) {
    Map<String, Object> row = executed(sequence, capabilityId, "FAILED", result);
    row.put("completed", false);
    row.put("reason", reason);
    return row;
  }

  private static Map<String, Object> impeded(int sequence, String capabilityId, String reason) {
    Map<String, Object> row = new LinkedHashMap<>();
    row.put("sequence", sequence);
    row.put("capabilityId", capabilityId);
    row.put("availability", "NOT_AVAILABLE");
    row.put("completed", false);
    row.put("reason", reason);
    return row;
  }

  private static Map<String, Object> projection(
      boolean authenticated,
      boolean dispatched,
      List<Map<String, Object>> steps,
      Map<String, Map<String, Object>> results,
      String subjectRef,
      Parameters.Present present) {
    Map<String, Object> summary = new LinkedHashMap<>();
    summary.put("kind", dispatched ? "WORKING_CAPITAL_EXECUTION" : "WORKING_CAPITAL_PLAN_IMPEDIMENTS");
    summary.put("intent", SatelliteContractV1.SEEK_WORKING_CAPITAL);
    summary.put("planId", SatelliteContractV1.WORKING_CAPITAL_PLAN);
    summary.put("analysisComplete", false);
    summary.put("providerDispatched", dispatched);
    summary.put("authenticatedCustomerPrincipal", authenticated);
    summary.put("subjectRef", subjectRef);
    summary.put("steps", steps);
    summary.put("impediments", steps.stream().filter(step -> !Boolean.TRUE.equals(step.get("completed"))).toList());
    if (present != null) {
      summary.put("requestedPrincipalCents", present.principalCents());
      summary.put("requestedTermMonths", present.termMonths());
    }
    return summary;
  }

  private static String explanation(Bundle bundle) {
    return switch (bundle.status()) {
      case "READY" ->
          "A Spider executou o plano WORKING_CAPITAL_DIAGNOSTIC_V1 com sistemas simulados. A simulação não é análise de crédito, oferta nem contratação.";
      case "MISSING_CONTEXT" -> "A jornada demonstrativa precisa de complemento específico antes de continuar.";
      case "PENDING" -> "Há uma pendência humana sintética. Nenhuma fila real foi aberta.";
      case "PROVIDER_UNAVAILABLE" -> "O executor simulado de crédito não respondeu de forma utilizável.";
      case "REJECTED" -> "O executor sintético recusou ou não encontrou alternativa elegível. Isso não é uma decisão de crédito real.";
      default ->
          "A Spider mapeou SEEK_WORKING_CAPITAL e WORKING_CAPITAL_DIAGNOSTIC_V1, mas a execução demonstrativa não pôde concluir.";
    };
  }

  private static Parameters parameters(SatelliteInteractionRequest request) {
    Object raw = extension(request, "workingCapitalParameters");
    if (!(raw instanceof Map<?, ?> map)) {
      return new Parameters.Missing(List.of("principalCents", "termMonths"));
    }
    Object principal = map.get("principalCents");
    Object term = map.get("termMonths");
    List<String> missing = new ArrayList<>();
    if (principal == null || String.valueOf(principal).isBlank()) {
      missing.add("principalCents");
    }
    if (term == null || String.valueOf(term).isBlank()) {
      missing.add("termMonths");
    }
    if (!missing.isEmpty()) {
      return new Parameters.Missing(missing);
    }
    long cents;
    int months;
    try {
      cents = Long.parseLong(String.valueOf(principal));
      months = Integer.parseInt(String.valueOf(term));
    } catch (NumberFormatException e) {
      return new Parameters.Invalid("INVALID_PAYLOAD", "Valor ou prazo declarado é inválido.");
    }
    if (cents < 10000 || cents > 100000000 || months < 1 || months > 36) {
      return new Parameters.Invalid("INVALID_PAYLOAD", "Valor ou prazo declarado está fora da faixa demonstrativa.");
    }
    Object origin = map.get("origin");
    if (origin != null && !"USER_DECLARED".equals(String.valueOf(origin))) {
      return new Parameters.Invalid("INVALID_PAYLOAD", "A origem dos parâmetros precisa ser USER_DECLARED.");
    }
    return new Parameters.Present(cents, months);
  }

  private static Object extension(SatelliteInteractionRequest request, String key) {
    if (request.extensions() == null) {
      return null;
    }
    return request.extensions().get(key);
  }

  private SatelliteInteractionService.Outcome response(
      SatelliteInteractionRequest request,
      String contextRef,
      String status,
      String requiredAction,
      String explanation,
      List<String> missing,
      Map<String, Object> summary) {
    return response(request, contextRef, status, requiredAction, explanation, missing, summary, "spd-" + UUID.randomUUID());
  }

  private SatelliteInteractionService.Outcome response(
      SatelliteInteractionRequest request,
      String contextRef,
      String status,
      String requiredAction,
      String explanation,
      List<String> missing,
      Map<String, Object> summary,
      String decisionId) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contractVersion", request.contractVersion());
    body.put("decisionId", decisionId);
    body.put("status", status);
    body.put("requiredAction", requiredAction);
    body.put("resultSummary", summary);
    body.put("missingContext", missing);
    body.put("nextInteraction", null);
    body.put("correlationId", request.correlationId());
    body.put("contextRef", contextRef);
    body.put("explainabilityRef", "sat-exp-" + decisionId);
    body.put("watermark", SatelliteContractV1.WATERMARK_CREDIT);
    body.put("explanation", explanation);
    body.put("originProvenance", request.provenanceMap());
    body.put("spiderPath", SatelliteContractV1.PATH_V1);
    body.put("capabilityId", "PRESENT_OPTIONS");
    body.put("providerRequestId", null);
    return SatelliteInteractionService.Outcome.ok(body);
  }

  private void emit(
      OperationalEventType type,
      SatelliteInteractionRequest request,
      OperationalEventOutcome outcome,
      String reason) {
    if (events == null || request == null) {
      return;
    }
    OperationalEventAttributes.Builder attributes =
        OperationalEventAttributes.builder().component("satellite-contract").reasonCode(reason);
    attributes.put("satelliteId", request.satelliteId());
    attributes.put("originSatellite", request.satelliteId());
    attributes.put("currentComponent", "SPIDER");
    attributes.put("contractVersion", request.contractVersion());
    attributes.put("aiUsage", "NOT_USED");
    if (type == OperationalEventType.PROVIDER_RESULT_RECEIVED) {
      attributes.put("executor", reason);
    }
    attributes.put("role", request.satelliteRole());
    OperationalEventEmit.publish(
        events,
        OperationalEventEmit.draft(
            type, request.messageId(), request.correlationId(), "satellite-contract", outcome, null, attributes.build()));
  }

  public record Attempt(boolean handled, SatelliteInteractionService.Outcome outcome) {
    static Attempt skip() {
      return new Attempt(false, null);
    }

    static Attempt done(SatelliteInteractionService.Outcome outcome) {
      return new Attempt(true, outcome);
    }
  }

  private sealed interface Parameters {
    record Missing(List<String> fields) implements Parameters {}

    record Invalid(String code, String message) implements Parameters {}

    record Present(long principalCents, int termMonths) implements Parameters {}
  }

  private record Bundle(
      String status,
      String requiredAction,
      List<String> missing,
      List<Map<String, Object>> steps,
      Map<String, Map<String, Object>> results,
      boolean providerDispatched) {}
}
