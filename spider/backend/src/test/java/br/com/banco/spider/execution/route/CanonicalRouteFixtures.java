package br.com.banco.spider.execution.route;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.ContextReference;
import br.com.banco.spider.canonical.contract.ContractDescriptor;
import br.com.banco.spider.canonical.contract.ExecutionIdentity;
import br.com.banco.spider.canonical.contract.ExecutionPolicyReference;
import br.com.banco.spider.canonical.contract.OriginDescriptor;
import br.com.banco.spider.canonical.contract.TargetDescriptor;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.canonical.versioning.VersionedReference;
import br.com.banco.spider.execution.mapping.StepInputMappingKind;
import br.com.banco.spider.integration.binding.ConfiguredAdapterBindingResolver;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/** Fixtures controladas para vertical slice canônica (dev/test). */
public final class CanonicalRouteFixtures {

  public static final String JOURNEY = "j@1";
  public static final String CAPABILITY = "CAP";
  public static final String OPERATION = "OP";
  public static final String BINDING = ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING;

  public static final String WAIT_ASYNC = "policy:wait:default-async@1.0";
  public static final String WAIT_UNKNOWN = "policy:wait:default-unknown@1.0";

  private CanonicalRouteFixtures() {}

  public static RouteDefinition publishedSingleStep(String routeCode, int priority) {
    return publishedSingleStep(routeCode, "1.0.0", priority, IdempotencyClassification.OPTIONAL);
  }

  public static RouteDefinition publishedAsyncSingleStep(String routeCode, int priority) {
    RouteStepDefinition step =
        RouteStepDefinition.entryAsync(
            "step-1",
            CAPABILITY,
            OPERATION,
            BINDING,
            "contract:input@1.0",
            "contract:output@1.0",
            "policy:retry:default@1.0",
            IdempotencyClassification.OPTIONAL,
            WAIT_ASYNC);
    return new RouteDefinition(
        routeCode,
        "1.0.0",
        JOURNEY,
        RouteStatus.PUBLISHED,
        "contract:route-in@1.0",
        "contract:route-out@1.0",
        new RouteTarget(CAPABILITY, OPERATION),
        priority,
        List.of(step),
        "integrity:route-" + routeCode + "@1.0.0");
  }

  public static RouteDefinition publishedAsyncThenSync(String routeCode, int priority) {
    RouteStepDefinition s1 =
        RouteStepDefinition.entryAsync(
            "step-1",
            CAPABILITY,
            OPERATION,
            BINDING,
            "contract:input@1.0",
            "contract:output@1.0",
            "policy:retry:default@1.0",
            IdempotencyClassification.OPTIONAL,
            WAIT_ASYNC);
    RouteStepDefinition s2 =
        new RouteStepDefinition(
            "step-2",
            "CAP2",
            "OP2",
            BINDING,
            "contract:input2@1.0",
            "contract:output2@1.0",
            List.of("step-1"),
            StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA.toRef(),
            null,
            "policy:retry:default@1.0",
            null,
            IdempotencyClassification.OPTIONAL,
            RetrySafety.SAFE,
            null,
            null);
    return new RouteDefinition(
        routeCode,
        "1.0.0",
        JOURNEY,
        RouteStatus.PUBLISHED,
        "contract:route-in@1.0",
        "contract:route-out@1.0",
        new RouteTarget(CAPABILITY, OPERATION),
        priority,
        List.of(s2, s1),
        "integrity:route-" + routeCode + "@1.0.0");
  }

  public static RouteDefinition publishedSingleStep(
      String routeCode, String version, int priority, IdempotencyClassification idem) {
    RouteStepDefinition step =
        RouteStepDefinition.entry(
            "step-1",
            CAPABILITY,
            OPERATION,
            BINDING,
            "contract:input@1.0",
            "contract:output@1.0",
            "policy:timeout@1.0",
            "policy:retry:default@1.0",
            null,
            idem,
            "policy:evidence@1.0");
    return new RouteDefinition(
        routeCode,
        version,
        JOURNEY,
        RouteStatus.PUBLISHED,
        "contract:route-in@1.0",
        "contract:route-out@1.0",
        new RouteTarget(CAPABILITY, OPERATION),
        priority,
        List.of(step),
        "integrity:route-" + routeCode + "@" + version);
  }

  public static RouteDefinition publishedLinearTwoSteps(String routeCode, int priority) {
    RouteStepDefinition s1 =
        RouteStepDefinition.entry(
            "step-1",
            CAPABILITY,
            OPERATION,
            BINDING,
            "contract:input@1.0",
            "contract:output@1.0",
            null,
            "policy:retry:default@1.0",
            null,
            IdempotencyClassification.OPTIONAL,
            null);
    RouteStepDefinition s2 =
        new RouteStepDefinition(
            "step-2",
            "CAP2",
            "OP2",
            BINDING,
            "contract:input2@1.0",
            "contract:output2@1.0",
            List.of("step-1"),
            StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA.toRef(),
            null,
            "policy:retry:default@1.0",
            null,
            IdempotencyClassification.OPTIONAL,
            RetrySafety.SAFE,            null,            null);
    return new RouteDefinition(
        routeCode,
        "1.0.0",
        JOURNEY,
        RouteStatus.PUBLISHED,
        "contract:route-in@1.0",
        "contract:route-out@1.0",
        new RouteTarget(CAPABILITY, OPERATION),
        priority,
        List.of(s2, s1), // embaralhado de propósito
        "integrity:route-" + routeCode + "@1.0.0");
  }

  public static RouteDefinition draftRoute(String routeCode) {
    RouteStepDefinition step =
        RouteStepDefinition.entry(
            "step-1",
            CAPABILITY,
            OPERATION,
            BINDING,
            "contract:input@1.0",
            "contract:output@1.0",
            null,
            null,
            null,
            IdempotencyClassification.OPTIONAL,
            null);
    return new RouteDefinition(
        routeCode,
        "1.0.0",
        JOURNEY,
        RouteStatus.DRAFT,
        "contract:route-in@1.0",
        "contract:route-out@1.0",
        new RouteTarget(CAPABILITY, OPERATION),
        10,
        List.of(step),
        null);
  }

  public static CanonicalExecutionRequest request(String executionId, String idempotencyKey) {
    return request(executionId, idempotencyKey, null);
  }

  public static CanonicalExecutionRequest request(
      String executionId, String idempotencyKey, String mockScenario) {
    CanonicalPayload payload = CanonicalPayload.empty();
    if (mockScenario != null) {
      ObjectMapper mapper = new ObjectMapper();
      ObjectNode data = mapper.createObjectNode();
      data.put("mockScenario", mockScenario);
      payload = new CanonicalPayload(data);
    }
    return CanonicalExecutionRequest.builder()
        .contract(new ContractDescriptor("1.0", "1.0.0"))
        .execution(new ExecutionIdentity(executionId, Instant.parse("2026-01-01T00:00:00Z"), idempotencyKey))
        .contextRef(new ContextReference("c", "i@1", "cap@1", "p@1", JOURNEY))
        .origin(new OriginDescriptor("CH", "orig", null))
        .trace(
            new TraceDescriptor(
                "corr-" + executionId,
                "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                null))
        .target(new TargetDescriptor(CAPABILITY, OPERATION))
        .payload(payload)
        .executionPolicy(ExecutionPolicyReference.empty())
        .callbackRef(VersionedReference.of("callback:default", "1.0.0"))
        .build();
  }

  public static List<RouteStepDefinition> shuffledChain(RouteStepDefinition... steps) {
    List<RouteStepDefinition> list = new ArrayList<>(List.of(steps));
    // reverse to force orderer independence
    java.util.Collections.reverse(list);
    return list;
  }
}
