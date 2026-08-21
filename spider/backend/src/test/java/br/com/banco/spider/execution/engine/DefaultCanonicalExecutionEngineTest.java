package br.com.banco.spider.execution.engine;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.validation.CanonicalStructuralValidator;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.mapping.ExplicitStepInputMapper;
import br.com.banco.spider.execution.persistence.support.InMemoryPersistenceBundle;
import br.com.banco.spider.execution.plan.DeterministicExecutionPlanMaterializer;
import br.com.banco.spider.execution.retry.ConfiguredRetryPolicyCatalog;
import br.com.banco.spider.execution.retry.RetryPolicyDefinition;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.DeterministicRouteResolver;
import br.com.banco.spider.execution.route.IdempotencyClassification;
import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteDefinitionValidator;
import br.com.banco.spider.execution.route.RouteStepDefinition;
import br.com.banco.spider.execution.step.IntermediateStepOutputStore;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.integration.binding.ConfiguredAdapterBindingResolver;
import br.com.banco.spider.integration.mock.MockUniversalAdapter;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

class DefaultCanonicalExecutionEngineTest {

  private final Instant fixed = Instant.parse("2026-07-21T15:00:00Z");
  private InMemoryPersistenceBundle persistence;
  private IdentifierGenerator ids;
  private IntermediateStepOutputStore outputs;
  private ExplicitStepInputMapper mapping;
  private ConfiguredRetryPolicyCatalog policies;

  @BeforeEach
  void setUp() {
    ids = IdentifierGenerator.sequential("t");
    persistence = new InMemoryPersistenceBundle(SpiderClock.fixed(fixed), ids);
    outputs = new IntermediateStepOutputStore();
    mapping = new ExplicitStepInputMapper(new ObjectMapper());
    policies =
        new ConfiguredRetryPolicyCatalog(
            List.of(RetryPolicyDefinition.publishedTechnical("default", "1.0", 3)));
  }

  private DefaultCanonicalExecutionEngine engine(
      List<br.com.banco.spider.execution.route.RouteDefinition> routes, UniversalAdapterPort adapter) {
    return new DefaultCanonicalExecutionEngine(
        new CanonicalStructuralValidator(),
        new DeterministicRouteResolver(new InMemoryRouteCatalog(routes), new RouteDefinitionValidator()),
        new DeterministicExecutionPlanMaterializer(
            ids, SpiderClock.fixed(fixed), IntegrityDigestPort.sha256()),
        new ConfiguredAdapterBindingResolver(
            Map.of(ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING, adapter)),
        persistence.gateway,
        persistence.keyHash,
        persistence.retryExecutor,
        mapping,
        policies,
        persistence.stepStore,
        outputs,
        persistence.waitCreation,
        ids,
        SpiderClock.fixed(fixed));
  }

  @Test
  void invalidRequestRejectedWithoutAdapter() {
    AtomicBoolean called = new AtomicBoolean(false);
    UniversalAdapterPort adapter =
        req -> {
          called.set(true);
          return Mono.empty();
        };
    var request =
        br.com.banco.spider.canonical.contract.CanonicalExecutionRequest.builder()
            .contract(new br.com.banco.spider.canonical.contract.ContractDescriptor("1.0", "1.0.0"))
            .execution(
                new br.com.banco.spider.canonical.contract.ExecutionIdentity(
                    "e-bad", fixed, "idem"))
            .contextRef(
                new br.com.banco.spider.canonical.contract.ContextReference(
                    "c", "i@1", "cap@1", "p@1", CanonicalRouteFixtures.JOURNEY))
            .origin(new br.com.banco.spider.canonical.contract.OriginDescriptor("CH", "o", null))
            .trace(
                new br.com.banco.spider.canonical.contract.TraceDescriptor(
                    "corr", "not-a-valid-traceparent", null))
            .target(
                new br.com.banco.spider.canonical.contract.TargetDescriptor(
                    CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION))
            .payload(br.com.banco.spider.canonical.contract.CanonicalPayload.empty())
            .callbackRef(
                br.com.banco.spider.canonical.versioning.VersionedReference.of(
                    "callback:default", "1.0.0"))
            .build();

    StepVerifier.create(
            engine(List.of(CanonicalRouteFixtures.publishedSingleStep("r", 1)), adapter)
                .execute(request))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.REJECTED, result.state());
              assertFalse(called.get());
            })
        .verifyComplete();
  }

  @Test
  void routeMissingRejectedWithoutAdapter() {
    AtomicBoolean called = new AtomicBoolean(false);
    UniversalAdapterPort adapter =
        req -> {
          called.set(true);
          return Mono.empty();
        };
    StepVerifier.create(
            engine(List.of(), adapter).execute(CanonicalRouteFixtures.request("e1", "idem")))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.REJECTED, result.state());
              assertFalse(called.get());
            })
        .verifyComplete();
  }

  @Test
  void ambiguousRouteRejectedWithoutAdapter() {
    AtomicInteger calls = new AtomicInteger();
    UniversalAdapterPort adapter =
        req -> {
          calls.incrementAndGet();
          return Mono.empty();
        };
    var a = CanonicalRouteFixtures.publishedSingleStep("a", 10);
    var b = CanonicalRouteFixtures.publishedSingleStep("b", 10);
    StepVerifier.create(
            engine(List.of(a, b), adapter).execute(CanonicalRouteFixtures.request("e1", "idem")))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.REJECTED, result.state());
              assertEquals(0, calls.get());
            })
        .verifyComplete();
  }

  @Test
  void successPathPersistsAndTransitions() {
    UniversalAdapterPort mock = new MockUniversalAdapter(new ObjectMapper());
    StepVerifier.create(
            engine(List.of(CanonicalRouteFixtures.publishedSingleStep("r", 1)), mock)
                .execute(CanonicalRouteFixtures.request("e-ok", "idem", "SUCCESS")))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.SUCCEEDED, result.state());
              assertEquals(TechnicalStatus.SUCCESS, result.outcome().technicalStatus());
              assertNotNull(result.resolution());
              assertEquals("r", result.resolution().routeId());
            })
        .verifyComplete();

    assertTrue(persistence.controlStore.findByExecutionId("e-ok").isPresent());
    assertTrue(persistence.planStore.findByExecutionId("e-ok").isPresent());
    assertTrue(persistence.stepStore.find("e-ok", "step-1").isPresent());
    assertTrue(persistence.resultStore.findByExecutionId("e-ok").isPresent());
  }

  @Test
  void twoStepsSuccess() {
    UniversalAdapterPort mock = new MockUniversalAdapter(new ObjectMapper());
    StepVerifier.create(
            engine(List.of(CanonicalRouteFixtures.publishedLinearTwoSteps("r2", 1)), mock)
                .execute(CanonicalRouteFixtures.request("e-2s", "idem", "SUCCESS")))
        .assertNext(result -> assertEquals(ExecutionState.SUCCEEDED, result.state()))
        .verifyComplete();
    assertEquals(
        br.com.banco.spider.execution.step.StepState.SUCCEEDED,
        persistence.stepStore.find("e-2s", "step-1").orElseThrow().state());
    assertEquals(
        br.com.banco.spider.execution.step.StepState.SUCCEEDED,
        persistence.stepStore.find("e-2s", "step-2").orElseThrow().state());
  }

  @Test
  void businessNegativeRemainsTechnicalSuccess() {
    UniversalAdapterPort mock = new MockUniversalAdapter(new ObjectMapper());
    StepVerifier.create(
            engine(List.of(CanonicalRouteFixtures.publishedSingleStep("r", 1)), mock)
                .execute(CanonicalRouteFixtures.request("e-biz", "idem", "BUSINESS_NEGATIVE")))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.SUCCEEDED, result.state());
              assertEquals(TechnicalStatus.SUCCESS, result.outcome().technicalStatus());
            })
        .verifyComplete();
  }

  @Test
  void technicalFailureMapsToFailed() {
    UniversalAdapterPort mock = new MockUniversalAdapter(new ObjectMapper());
    StepVerifier.create(
            engine(List.of(CanonicalRouteFixtures.publishedSingleStep("r", 1)), mock)
                .execute(CanonicalRouteFixtures.request("e-fail", "idem", "TECHNICAL_FAILURE")))
        .assertNext(result -> assertEquals(ExecutionState.FAILED, result.state()))
        .verifyComplete();
  }

  @Test
  void timeoutMapsToTimedOut() {
    UniversalAdapterPort mock = new MockUniversalAdapter(new ObjectMapper());
    StepVerifier.create(
            engine(List.of(CanonicalRouteFixtures.publishedSingleStep("r", 1)), mock)
                .execute(CanonicalRouteFixtures.request("e-to", "idem", "TIMEOUT")))
        .assertNext(result -> assertEquals(ExecutionState.TIMED_OUT, result.state()))
        .verifyComplete();
  }

  @Test
  void acceptedAsyncMapsToWaitingExternal() {
    UniversalAdapterPort mock = new MockUniversalAdapter(new ObjectMapper());
    StepVerifier.create(
            engine(List.of(CanonicalRouteFixtures.publishedAsyncSingleStep("r", 1)), mock)
                .execute(CanonicalRouteFixtures.request("e-async", "idem", "ACCEPTED_ASYNC")))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.WAITING_EXTERNAL, result.state());
              assertTrue(
                  persistence.waitStore.findActiveByExecutionAndStep("e-async", "step-1").isPresent());
            })
        .verifyComplete();
  }

  @Test
  void unknownMapsToWaitingWithoutRetry() {
    AtomicInteger calls = new AtomicInteger();
    UniversalAdapterPort counting =
        req -> {
          calls.incrementAndGet();
          return new MockUniversalAdapter(new ObjectMapper()).invoke(req);
        };
    RouteStepDefinition step =
        RouteStepDefinition.entryAsync(
            "step-1",
            CanonicalRouteFixtures.CAPABILITY,
            CanonicalRouteFixtures.OPERATION,
            CanonicalRouteFixtures.BINDING,
            "contract:input@1.0",
            "contract:output@1.0",
            "policy:retry:default@1.0",
            IdempotencyClassification.OPTIONAL,
            CanonicalRouteFixtures.WAIT_UNKNOWN);
    var route =
        new br.com.banco.spider.execution.route.RouteDefinition(
            "r-unk",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            br.com.banco.spider.execution.route.RouteStatus.PUBLISHED,
            "contract:route-in@1.0",
            "contract:route-out@1.0",
            new br.com.banco.spider.execution.route.RouteTarget(
                CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION),
            1,
            List.of(step),
            "integrity:r-unk@1.0.0");
    StepVerifier.create(
            engine(List.of(route), counting)
                .execute(CanonicalRouteFixtures.request("e-unk", "idem", "UNKNOWN")))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.WAITING_EXTERNAL, result.state());
              assertEquals(1, calls.get());
            })
        .verifyComplete();
  }

  @Test
  void idempotencyRequiredWithoutKeyRejectedBeforeAdapter() {
    AtomicBoolean called = new AtomicBoolean(false);
    UniversalAdapterPort adapter =
        req -> {
          called.set(true);
          return Mono.empty();
        };
    var route =
        CanonicalRouteFixtures.publishedSingleStep(
            "r-idem", "1.0.0", 1, IdempotencyClassification.REQUIRED);
    StepVerifier.create(
            engine(List.of(route), adapter).execute(CanonicalRouteFixtures.request("e-idem", null)))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.REJECTED, result.state());
              assertFalse(called.get());
            })
        .verifyComplete();
  }

  @Test
  void completedReuseDoesNotCallAdapterAgain() {
    AtomicInteger calls = new AtomicInteger();
    UniversalAdapterPort counting =
        req -> {
          calls.incrementAndGet();
          return new MockUniversalAdapter(new ObjectMapper()).invoke(req);
        };
    var routes = List.of(CanonicalRouteFixtures.publishedSingleStep("r", 1));
    var eng = engine(routes, counting);

    StepVerifier.create(eng.execute(CanonicalRouteFixtures.request("e-reuse-1", "same-key", "SUCCESS")))
        .assertNext(r -> assertEquals(ExecutionState.SUCCEEDED, r.state()))
        .verifyComplete();

    StepVerifier.create(eng.execute(CanonicalRouteFixtures.request("e-reuse-2", "same-key", "SUCCESS")))
        .assertNext(r -> assertEquals(ExecutionState.SUCCEEDED, r.state()))
        .verifyComplete();

    assertEquals(1, calls.get());
  }
}
