package br.com.banco.spider.application.console;

import br.com.banco.spider.execution.mapping.StepInputMappingKind;
import br.com.banco.spider.execution.route.IdempotencyClassification;
import br.com.banco.spider.execution.route.RetrySafety;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.route.RouteStatus;
import br.com.banco.spider.execution.route.RouteStepDefinition;
import br.com.banco.spider.execution.route.RouteTarget;
import br.com.banco.spider.integration.binding.ConfiguredAdapterBindingResolver;
import br.com.banco.spider.operational.failurelab.FailureLabRouteSupport;
import java.util.List;

/**
 * Rotas publicadas da aba Simulação. Não republica {@code RETRY_THEN_SUCCESS} — essa operação já
 * existe no catálogo do Failure Lab. Os demais códigos batem com o que o Monitor já consulta.
 */
public final class DemoCanonicalRouteSupport {

  public static final String CALLBACK_REF = "callback:console-local-demo";
  public static final String CALLBACK_VERSION = "1.0.0";
  public static final String CALLBACK_BINDING = "binding:mock-callback@1.0";
  public static final String CALLBACK_POLICY = "policy:cb-local-demo@1.0";

  private static final String BINDING = ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING;
  private static final String VERSION = "1.0.0";

  private DemoCanonicalRouteSupport() {}

  public static List<RouteDefinition> routes() {
    return List.of(
        linearTwo("SUCCESS_MULTI_STEP", FailureLabRouteSupport.RETRY_POLICY_REF, 10),
        sync("BUSINESS_NEGATIVE", FailureLabRouteSupport.NO_RETRY_POLICY_REF, 10),
        async("WAIT_SIGNAL_RESUME", FailureLabRouteSupport.WAIT_ASYNC_POLICY_REF, 10),
        sync("CALLBACK_RECONCILIATION", FailureLabRouteSupport.NO_RETRY_POLICY_REF, 10),
        sync("TECHNICAL_FAILURE", FailureLabRouteSupport.NO_RETRY_POLICY_REF, 10));
  }

  public static String callbackExactRef() {
    return CALLBACK_REF + "@" + CALLBACK_VERSION;
  }

  private static RouteDefinition sync(String operationCode, String retryPolicyRef, int priority) {
    RouteStepDefinition step =
        RouteStepDefinition.entry(
            "step-1",
            FailureLabRouteSupport.CAPABILITY_CODE,
            operationCode,
            BINDING,
            "contract:demo-input@1.0",
            "contract:demo-output@1.0",
            null,
            retryPolicyRef,
            null,
            IdempotencyClassification.OPTIONAL,
            null);
    return route(operationCode, priority, List.of(step));
  }

  private static RouteDefinition async(String operationCode, String waitPolicyRef, int priority) {
    RouteStepDefinition step =
        RouteStepDefinition.entryAsync(
            "step-1",
            FailureLabRouteSupport.CAPABILITY_CODE,
            operationCode,
            BINDING,
            "contract:demo-input@1.0",
            "contract:demo-output@1.0",
            FailureLabRouteSupport.NO_RETRY_POLICY_REF,
            IdempotencyClassification.OPTIONAL,
            waitPolicyRef);
    return route(operationCode, priority, List.of(step));
  }

  private static RouteDefinition linearTwo(String operationCode, String retryPolicyRef, int priority) {
    RouteStepDefinition first =
        RouteStepDefinition.entry(
            "step-1",
            FailureLabRouteSupport.CAPABILITY_CODE,
            operationCode,
            BINDING,
            "contract:demo-input@1.0",
            "contract:demo-output@1.0",
            null,
            retryPolicyRef,
            null,
            IdempotencyClassification.OPTIONAL,
            null);
    RouteStepDefinition second =
        new RouteStepDefinition(
            "step-2",
            FailureLabRouteSupport.CAPABILITY_CODE,
            operationCode,
            BINDING,
            "contract:demo-input@1.0",
            "contract:demo-output@1.0",
            List.of("step-1"),
            StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA.toRef(),
            null,
            retryPolicyRef,
            null,
            IdempotencyClassification.OPTIONAL,
            RetrySafety.SAFE,
            null,
            null);
    return route(operationCode, priority, List.of(first, second));
  }

  private static RouteDefinition route(
      String operationCode, int priority, List<RouteStepDefinition> steps) {
    String routeCode = "demo-" + operationCode.toLowerCase(java.util.Locale.ROOT);
    return new RouteDefinition(
        routeCode,
        VERSION,
        FailureLabRouteSupport.JOURNEY_REF,
        RouteStatus.PUBLISHED,
        "contract:demo-route-in@1.0",
        "contract:demo-route-out@1.0",
        new RouteTarget(FailureLabRouteSupport.CAPABILITY_CODE, operationCode),
        priority,
        steps,
        "integrity:route-" + routeCode + "@" + VERSION);
  }
}
