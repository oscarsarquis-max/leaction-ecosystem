package br.com.banco.spider.operational.failurelab;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.ContextReference;
import br.com.banco.spider.canonical.contract.ContractDescriptor;
import br.com.banco.spider.canonical.contract.ExecutionIdentity;
import br.com.banco.spider.canonical.contract.ExecutionPolicyReference;
import br.com.banco.spider.canonical.contract.OriginDescriptor;
import br.com.banco.spider.canonical.contract.TargetDescriptor;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.execution.engine.CanonicalExecutionEngine;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.security.SecureRandom;
import java.util.HexFormat;
import reactor.core.publisher.Mono;

/**
 * Monta e submete o pedido canônico do laboratório. A Engine recebe um pedido comum — a origem
 * {@code failure-lab} é apenas um dado de contexto, nunca um desvio de comportamento.
 */
public class FailureLabSubmitSupport {

  public static final String ORIGIN_CHANNEL = "failure-lab";
  public static final String ORIGINATOR_ID = "failure-lab-operator";
  public static final String ORIGIN_MARKER = "FAILURE_LAB";

  private final CanonicalExecutionEngine engine;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final ObjectMapper mapper;

  private static final SecureRandom RANDOM = new SecureRandom();

  public FailureLabSubmitSupport(
      CanonicalExecutionEngine engine,
      IdentifierGenerator ids,
      SpiderClock clock,
      ObjectMapper mapper) {
    this.engine = engine;
    this.ids = ids;
    this.clock = clock;
    this.mapper = mapper;
  }

  public record SubmitOutcome(String executionId, CanonicalExecutionResult result) {}

  public Mono<SubmitOutcome> submit(FailureScenarioDefinition scenario, String labRunId) {
    String executionId = ids.nextId("exec");
    CanonicalExecutionRequest request = buildRequest(scenario, labRunId, executionId);
    return engine
        .execute(request)
        .map(result -> new SubmitOutcome(executionId, result))
        .defaultIfEmpty(new SubmitOutcome(executionId, null));
  }

  CanonicalExecutionRequest buildRequest(
      FailureScenarioDefinition scenario, String labRunId, String executionId) {
    ObjectNode canonicalData = mapper.createObjectNode();
    canonicalData.put("mockScenario", scenario.mockScenario());
    canonicalData.put("labRunId", labRunId);
    canonicalData.put("failureLabOrigin", ORIGIN_MARKER);

    return CanonicalExecutionRequest.builder()
        .contract(new ContractDescriptor("1.0", "1.0.0"))
        .execution(new ExecutionIdentity(executionId, clock.now(), executionId))
        .contextRef(
            new ContextReference(
                "ctx:failure-lab",
                "intent:failure-lab@1.0",
                "capability:mock@1.0",
                "product:failure-lab@1.0",
                FailureLabRouteSupport.JOURNEY_REF))
        .origin(new OriginDescriptor(ORIGIN_CHANNEL, ORIGINATOR_ID, labRunId))
        .trace(
            new TraceDescriptor("corr-" + labRunId + "-" + executionId, newTraceparent(), null))
        .target(
            new TargetDescriptor(FailureLabRouteSupport.CAPABILITY_CODE, scenario.operationCode()))
        .payload(CanonicalPayload.of(canonicalData))
        .executionPolicy(ExecutionPolicyReference.empty())
        .build();
  }

  /** Traceparent W3C válido para correlacionar a execução controlada. */
  public static String newTraceparent() {
    byte[] traceId = new byte[16];
    byte[] spanId = new byte[8];
    RANDOM.nextBytes(traceId);
    RANDOM.nextBytes(spanId);
    traceId[0] |= 1;
    spanId[0] |= 1;
    HexFormat hex = HexFormat.of();
    return "00-" + hex.formatHex(traceId) + "-" + hex.formatHex(spanId) + "-01";
  }
}
