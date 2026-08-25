package br.com.banco.spider.operational.failurelab;

import br.com.banco.spider.execution.retry.RetryPolicyDefinition;
import br.com.banco.spider.execution.route.IdempotencyClassification;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.route.RouteStatus;
import br.com.banco.spider.execution.route.RouteStepDefinition;
import br.com.banco.spider.execution.route.RouteTarget;
import br.com.banco.spider.execution.wait.WaitPolicyDefinition;
import br.com.banco.spider.integration.binding.ConfiguredAdapterBindingResolver;
import java.time.Duration;
import java.util.List;

/**
 * Rotas e políticas publicadas exclusivamente para o Failure Lab. Todas apontam para o binding mock
 * — a Engine continua sem qualquer conhecimento do laboratório.
 */
public final class FailureLabRouteSupport {

  public static final String JOURNEY_REF = "journey:mock";
  public static final String CAPABILITY_CODE = "mock";

  public static final String RETRY_POLICY_REF = "policy:retry:default@1.0";
  public static final String NO_RETRY_POLICY_REF = "policy:retry:no-retry@1.0";
  public static final String WAIT_ASYNC_POLICY_REF = "policy:wait:default-async@1.0";
  public static final String WAIT_UNKNOWN_POLICY_REF = "policy:wait:default-unknown@1.0";

  public static final String MOCK_ASYNC_SOURCE_REF = "source:mock-async@1.0";

  public static final String OPERATION_RETRY_THEN_SUCCESS = "RETRY_THEN_SUCCESS";
  public static final String OPERATION_TECHNICAL_TERMINAL_FAILURE = "TECHNICAL_TERMINAL_FAILURE";
  public static final String OPERATION_WAIT_AND_RESUME = "WAIT_AND_RESUME";
  public static final String OPERATION_SIGNAL_SECURITY_REJECTED = "SIGNAL_SECURITY_REJECTED";
  public static final String OPERATION_CALLBACK_UNCERTAIN = "CALLBACK_UNCERTAIN";
  public static final String OPERATION_OPERATIONAL_DEGRADATION = "OPERATIONAL_DEGRADATION";

  private static final String BINDING = ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING;
  private static final String VERSION = "1.0.0";

  private FailureLabRouteSupport() {}

  public static List<RouteDefinition> routes() {
    return List.of(
        syncRoute(OPERATION_RETRY_THEN_SUCCESS, RETRY_POLICY_REF, 10),
        syncRoute(OPERATION_TECHNICAL_TERMINAL_FAILURE, NO_RETRY_POLICY_REF, 10),
        asyncRoute(OPERATION_WAIT_AND_RESUME, WAIT_ASYNC_POLICY_REF, 10),
        asyncRoute(OPERATION_SIGNAL_SECURITY_REJECTED, WAIT_ASYNC_POLICY_REF, 10),
        asyncRoute(OPERATION_CALLBACK_UNCERTAIN, WAIT_UNKNOWN_POLICY_REF, 10),
        syncRoute(OPERATION_OPERATIONAL_DEGRADATION, NO_RETRY_POLICY_REF, 10));
  }

  public static List<RetryPolicyDefinition> retryPolicies() {
    return List.of(
        RetryPolicyDefinition.publishedTechnical("default", "1.0", 3),
        RetryPolicyDefinition.noRetry("no-retry", "1.0"));
  }

  public static List<WaitPolicyDefinition> waitPolicies() {
    return List.of(
        WaitPolicyDefinition.publishedAsync(
            "default-async", "1.0", Duration.ofMinutes(5), List.of(MOCK_ASYNC_SOURCE_REF)),
        WaitPolicyDefinition.publishedUnknown(
            "default-unknown", "1.0", Duration.ofMinutes(5), List.of(MOCK_ASYNC_SOURCE_REF)));
  }

  private static RouteDefinition syncRoute(
      String operationCode, String retryPolicyRef, int priority) {
    RouteStepDefinition step =
        RouteStepDefinition.entry(
            "step-1",
            CAPABILITY_CODE,
            operationCode,
            BINDING,
            "contract:failure-lab-input@1.0",
            "contract:failure-lab-output@1.0",
            null,
            retryPolicyRef,
            null,
            IdempotencyClassification.OPTIONAL,
            null);
    return route(operationCode, priority, step);
  }

  private static RouteDefinition asyncRoute(
      String operationCode, String waitPolicyRef, int priority) {
    RouteStepDefinition step =
        RouteStepDefinition.entryAsync(
            "step-1",
            CAPABILITY_CODE,
            operationCode,
            BINDING,
            "contract:failure-lab-input@1.0",
            "contract:failure-lab-output@1.0",
            NO_RETRY_POLICY_REF,
            IdempotencyClassification.OPTIONAL,
            waitPolicyRef);
    return route(operationCode, priority, step);
  }

  private static RouteDefinition route(
      String operationCode, int priority, RouteStepDefinition step) {
    String routeCode = "failure-lab-" + operationCode.toLowerCase(java.util.Locale.ROOT);
    return new RouteDefinition(
        routeCode,
        VERSION,
        JOURNEY_REF,
        RouteStatus.PUBLISHED,
        "contract:failure-lab-route-in@1.0",
        "contract:failure-lab-route-out@1.0",
        new RouteTarget(CAPABILITY_CODE, operationCode),
        priority,
        List.of(step),
        "integrity:route-" + routeCode + "@" + VERSION);
  }
}
