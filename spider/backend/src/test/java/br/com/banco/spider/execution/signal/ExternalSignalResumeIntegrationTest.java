package br.com.banco.spider.execution.signal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.canonical.validation.CanonicalStructuralValidator;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.engine.DefaultCanonicalExecutionEngine;
import br.com.banco.spider.execution.mapping.ExplicitStepInputMapper;
import br.com.banco.spider.execution.persistence.support.InMemoryPersistenceBundle;
import br.com.banco.spider.execution.plan.DeterministicExecutionPlanMaterializer;
import br.com.banco.spider.execution.retry.ConfiguredRetryPolicyCatalog;
import br.com.banco.spider.execution.retry.RetryPolicyDefinition;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.DeterministicRouteResolver;
import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteDefinitionValidator;
import br.com.banco.spider.execution.step.IntermediateStepOutputStore;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.WaitExpiryProcessor;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.integration.binding.ConfiguredAdapterBindingResolver;
import br.com.banco.spider.integration.mock.MockUniversalAdapter;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class ExternalSignalResumeIntegrationTest {

  private final Instant fixed = Instant.parse("2026-07-21T20:00:00Z");
  private InMemoryPersistenceBundle persistence;
  private IdentifierGenerator ids;
  private DefaultExternalSignalApplicationService signals;
  private DefaultCanonicalExecutionEngine engine;
  private IntermediateStepOutputStore outputs;
  private Sha256ExternalSignalFingerprint fingerprint;

  @BeforeEach
  void setUp() {
    ids = IdentifierGenerator.sequential("s");
    SpiderClock clock = SpiderClock.fixed(fixed);
    persistence = new InMemoryPersistenceBundle(clock, ids);
    outputs = new IntermediateStepOutputStore();
    fingerprint = new Sha256ExternalSignalFingerprint();
    ExplicitStepInputMapper mapping = new ExplicitStepInputMapper(new ObjectMapper());
    var retryPolicies =
        new ConfiguredRetryPolicyCatalog(
            List.of(RetryPolicyDefinition.publishedTechnical("default", "1.0", 2)));
    var binding =
        new ConfiguredAdapterBindingResolver(
            Map.of(
                ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING,
                new MockUniversalAdapter(new ObjectMapper())));
    var resume =
        new ExecutionResumeService(
            persistence.waitStore,
            persistence.stepStore,
            persistence.attemptStore,
            persistence.gateway,
            outputs,
            persistence.retryExecutor,
            mapping,
            retryPolicies,
            binding,
            IntegrityDigestPort.sha256(),
            clock);
    signals =
        new DefaultExternalSignalApplicationService(
            persistence.inboxStore,
            persistence.waitStore,
            persistence.stepStore,
            fingerprint,
            fingerprint,
            new ConfiguredExternalSignalAuthorization(),
            new ExternalSignalValidator(clock),
            resume,
            clock);
    engine =
        new DefaultCanonicalExecutionEngine(
            new CanonicalStructuralValidator(),
            new DeterministicRouteResolver(
                new InMemoryRouteCatalog(
                    List.of(CanonicalRouteFixtures.publishedAsyncThenSync("async-r", 1))),
                new RouteDefinitionValidator()),
            new DeterministicExecutionPlanMaterializer(
                ids, clock, IntegrityDigestPort.sha256()),
            binding,
            persistence.gateway,
            persistence.keyHash,
            persistence.retryExecutor,
            mapping,
            retryPolicies,
            persistence.stepStore,
            outputs,
            persistence.waitCreation,
            ids,
            clock);
  }

  private ExternalSignalEnvelope successSignal(String executionId, String extOp, String messageId) {
    Instant now = fixed;
    return new ExternalSignalEnvelope(
        "1.0",
        messageId,
        "source:mock-async@1.0",
        ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING,
        "contract:signal:async-completion@1.0",
        executionId,
        "step-1",
        extOp,
        now,
        now,
        "corr-" + executionId,
        new TraceDescriptor(
            "corr-" + executionId,
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            null),
        new SignalSecurityContext(
            "principal:test-signal@1.0",
            "source:mock-async@1.0",
            "test",
            now.minusSeconds(60),
            now.plusSeconds(3600),
            "profile:signal:test@1.0",
            "ev-sec"),
        new SignalCompletion(
            AdapterDispositionMode.COMPLETED,
            CanonicalOutcome.technical(TechnicalStatus.SUCCESS),
            List.of(),
            List.of()));
  }

  @Test
  void asyncThenSignalSuccessRunsSecondStep() {
    AtomicInteger adapterCalls = new AtomicInteger();
    var countingAdapter =
        new br.com.banco.spider.integration.port.UniversalAdapterPort() {
          @Override
          public reactor.core.publisher.Mono<br.com.banco.spider.integration.port.UniversalAdapterResult>
              invoke(br.com.banco.spider.integration.port.UniversalAdapterRequest request) {
            adapterCalls.incrementAndGet();
            return new MockUniversalAdapter(new ObjectMapper()).invoke(request);
          }
        };
    var binding =
        new ConfiguredAdapterBindingResolver(
            Map.of(ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING, countingAdapter));
    // rebuild engine with counting adapter for second step visibility — use mock scenarios
    SpiderClock clock = SpiderClock.fixed(fixed);
    ExplicitStepInputMapper mapping = new ExplicitStepInputMapper(new ObjectMapper());
    var retryPolicies =
        new ConfiguredRetryPolicyCatalog(
            List.of(RetryPolicyDefinition.publishedTechnical("default", "1.0", 2)));
    engine =
        new DefaultCanonicalExecutionEngine(
            new CanonicalStructuralValidator(),
            new DeterministicRouteResolver(
                new InMemoryRouteCatalog(
                    List.of(CanonicalRouteFixtures.publishedAsyncThenSync("async-r", 1))),
                new RouteDefinitionValidator()),
            new DeterministicExecutionPlanMaterializer(
                ids, clock, IntegrityDigestPort.sha256()),
            binding,
            persistence.gateway,
            persistence.keyHash,
            persistence.retryExecutor,
            mapping,
            retryPolicies,
            persistence.stepStore,
            outputs,
            persistence.waitCreation,
            ids,
            clock);
    var resume =
        new ExecutionResumeService(
            persistence.waitStore,
            persistence.stepStore,
            persistence.attemptStore,
            persistence.gateway,
            outputs,
            persistence.retryExecutor,
            mapping,
            retryPolicies,
            binding,
            IntegrityDigestPort.sha256(),
            clock);
    signals =
        new DefaultExternalSignalApplicationService(
            persistence.inboxStore,
            persistence.waitStore,
            persistence.stepStore,
            fingerprint,
            fingerprint,
            new ConfiguredExternalSignalAuthorization(),
            new ExternalSignalValidator(clock),
            resume,
            clock);

    StepVerifier.create(
            engine.execute(CanonicalRouteFixtures.request("e-res", "idem", "ACCEPTED_ASYNC")))
        .assertNext(r -> assertEquals(ExecutionState.WAITING_EXTERNAL, r.state()))
        .verifyComplete();

    var wait =
        persistence.waitStore.findActiveByExecutionAndStep("e-res", "step-1").orElseThrow();
    assertEquals(WaitState.WAITING, wait.state());
    assertEquals(1, adapterCalls.get());

    StepVerifier.create(
            signals.process(
                successSignal("e-res", wait.externalOperationRef(), "msg-1")))
        .assertNext(
            pr -> {
              assertEquals(ExternalSignalProcessingStatus.ACCEPTED_AND_RESUMED, pr.processingStatus());
              assertEquals(StepState.SUCCEEDED, persistence.stepStore.find("e-res", "step-1").orElseThrow().state());
              assertEquals(StepState.SUCCEEDED, persistence.stepStore.find("e-res", "step-2").orElseThrow().state());
            })
        .verifyComplete();

    assertTrue(adapterCalls.get() >= 2);
  }

  @Test
  void duplicateDoesNotReinvoke() {
    StepVerifier.create(
            engine.execute(CanonicalRouteFixtures.request("e-dup", "idem", "ACCEPTED_ASYNC")))
        .assertNext(r -> assertEquals(ExecutionState.WAITING_EXTERNAL, r.state()))
        .verifyComplete();
    var wait = persistence.waitStore.findActiveByExecutionAndStep("e-dup", "step-1").orElseThrow();
    var signal = successSignal("e-dup", wait.externalOperationRef(), "msg-dup");

    StepVerifier.create(signals.process(signal))
        .assertNext(pr -> assertEquals(ExternalSignalProcessingStatus.ACCEPTED_AND_RESUMED, pr.processingStatus()))
        .verifyComplete();
    StepVerifier.create(signals.process(signal))
        .assertNext(pr -> assertEquals(ExternalSignalProcessingStatus.DUPLICATE, pr.processingStatus()))
        .verifyComplete();
  }

  @Test
  void orphanSignalMarked() {
    Instant now = fixed;
    var orphan =
        new ExternalSignalEnvelope(
            "1.0",
            "orphan-1",
            "source:mock-async@1.0",
            ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING,
            "contract:signal:async-completion@1.0",
            "no-exec",
            "step-1",
            "ext-x",
            now,
            now,
            "corr-x",
            new TraceDescriptor(
                "corr-x", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01", null),
            new SignalSecurityContext(
                "principal:test-signal@1.0",
                "source:mock-async@1.0",
                "test",
                now.minusSeconds(1),
                now.plusSeconds(3600),
                "profile:signal:test@1.0",
                null),
            new SignalCompletion(
                AdapterDispositionMode.COMPLETED,
                CanonicalOutcome.technical(TechnicalStatus.SUCCESS),
                List.of(),
                List.of()));
    StepVerifier.create(signals.process(orphan))
        .assertNext(pr -> assertEquals(ExternalSignalProcessingStatus.ORPHANED, pr.processingStatus()))
        .verifyComplete();
  }

  @Test
  void expiryIdempotent() {
    StepVerifier.create(
            engine.execute(CanonicalRouteFixtures.request("e-exp", "idem", "ACCEPTED_ASYNC")))
        .assertNext(r -> assertEquals(ExecutionState.WAITING_EXTERNAL, r.state()))
        .verifyComplete();
    var wait = persistence.waitStore.findActiveByExecutionAndStep("e-exp", "step-1").orElseThrow();
    // force expire by rewriting wait with past expiresAt via new insert isn't possible — use processor with clock past
    // Instead manually transition: create processor with future clock
    SpiderClock later = SpiderClock.fixed(wait.expiresAt().plusSeconds(1));
    WaitExpiryProcessor expiry =
        new WaitExpiryProcessor(
            persistence.waitStore,
            persistence.stepStore,
            persistence.attemptStore,
            persistence.gateway,
            persistence.waitPolicies,
            later);
    StepVerifier.create(expiry.expire(wait.waitId(), wait.stateVersion()))
        .assertNext(ok -> assertTrue(ok))
        .verifyComplete();
    StepVerifier.create(expiry.expire(wait.waitId(), wait.stateVersion()))
        .assertNext(ok -> assertEquals(false, ok))
        .verifyComplete();
    assertEquals(
        StepState.TIMED_OUT,
        persistence.stepStore.find("e-exp", "step-1").orElseThrow().state());
    assertEquals(
        StepState.SKIPPED,
        persistence.stepStore.find("e-exp", "step-2").orElseThrow().state());
  }
}
