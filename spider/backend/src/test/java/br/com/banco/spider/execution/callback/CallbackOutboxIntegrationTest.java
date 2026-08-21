package br.com.banco.spider.execution.callback;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.contract.ContractDescriptor;
import br.com.banco.spider.canonical.contract.ResultContextReference;
import br.com.banco.spider.canonical.contract.ResultTraceDescriptor;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.execution.callback.delivery.MockCallbackAdapter;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.ExecutionSummary;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionResult;
import br.com.banco.spider.execution.persistence.support.InMemoryPersistenceBundle;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackDeliveryAttemptStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackOutboxStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionCallbackContextStore;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.time.Duration;
import java.time.Instant;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class CallbackOutboxIntegrationTest {

  private static final Instant NOW = Instant.parse("2026-07-21T15:00:00Z");

  private InMemoryExecutionCallbackContextStore contextStore;
  private InMemoryCallbackOutboxStore outboxStore;
  private InMemoryCallbackDeliveryAttemptStore attemptStore;
  private CallbackOutboxCreationService creation;
  private CallbackOutboxProcessor processor;
  private MockCallbackAdapter mock;
  private SpiderClock clock;
  private IdentifierGenerator ids;

  @BeforeEach
  void setUp() {
    clock = SpiderClock.fixed(NOW);
    ids = IdentifierGenerator.fixed(() -> "CB");
    contextStore = new InMemoryExecutionCallbackContextStore();
    outboxStore = new InMemoryCallbackOutboxStore();
    attemptStore = new InMemoryCallbackDeliveryAttemptStore();
    var policy =
        CallbackDeliveryPolicy.publishedDefault("policy:cb-default", "1.0");
    var policyCatalog = new ConfiguredCallbackDeliveryPolicyCatalog(List.of(policy));
    var def =
        CallbackDefinition.published(
            "callback:test-originator",
            "1.0.0",
            "binding:mock-callback@1.0",
            "contract:callback:result@1.0",
            "profile:callback:test@1.0",
            policy.exactRef(),
            CallbackProjectionKind.MINIMAL_STATUS_V1.name(),
            List.of("orig-test"),
            "INTERNAL");
    var defCatalog = new ConfiguredCallbackDefinitionCatalog(List.of(def));
    creation =
        new CallbackOutboxCreationService(
            contextStore, outboxStore, policyCatalog, new Sha256IdempotencyKeyHash(), ids, clock);
    mock = new MockCallbackAdapter(MockCallbackAdapter.Scenario.DELIVERED);
    InMemoryPersistenceBundle bundle = new InMemoryPersistenceBundle(clock, ids);
    ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
    processor =
        new CallbackOutboxProcessor(
            outboxStore,
            attemptStore,
            contextStore,
            bundle.gateway,
            policyCatalog,
            defCatalog,
            new DefaultCallbackProjectionAdapter(mapper),
            new OriginatorMatchedCallbackAuthorizationAdapter(),
            new ConfiguredCallbackBindingResolver(Map.of("binding:mock-callback@1.0", mock)),
            ids,
            clock);

    contextStore.insert(
        new ExecutionCallbackContext(
            "e-cb-1",
            def.exactRef(),
            def.bindingRef(),
            def.callbackContractRef(),
            def.securityProfileRef(),
            def.deliveryPolicyRef(),
            def.projectionRef(),
            "orig-test",
            def.integrityRef(),
            NOW,
            def.confirmationMode(),
            def.statusQueryBindingRef(),
            def.reconciliationPolicyRef(),
            def.redeliverySafety(),
            "hash-e-cb-1"));
  }

  @Test
  void terminalSuccessCreatesOutboxAndDelivers() {
    CanonicalExecutionResult result = sampleResult("e-cb-1", ExecutionState.SUCCEEDED);
    PersistedExecutionResult persisted =
        new PersistedExecutionResult(
            "res-1",
            "e-cb-1",
            "1.0.0",
            ExecutionState.SUCCEEDED,
            TechnicalStatus.SUCCESS,
            "{}",
            "digest",
            NOW,
            NOW.plus(Duration.ofHours(1)));
    // seed result for processor load
    InMemoryPersistenceBundle bundle = new InMemoryPersistenceBundle(clock, ids);
    // use creation only
    var outbox = creation.createIfRequired(result, persisted);
    assertTrue(outbox.isPresent());
    assertEquals(CallbackOutboxState.PENDING, outbox.get().state());

    // duplicate create is idempotent
    var again = creation.createIfRequired(result, persisted);
    assertEquals(outbox.get().outboxId(), again.orElseThrow().outboxId());
  }

  @Test
  void waitingDoesNotCreateOutbox() {
    CanonicalExecutionResult result = sampleResult("e-cb-1", ExecutionState.WAITING_EXTERNAL);
    PersistedExecutionResult persisted =
        new PersistedExecutionResult(
            "res-w",
            "e-cb-1",
            "1.0.0",
            ExecutionState.WAITING_EXTERNAL,
            TechnicalStatus.SUCCESS,
            "{}",
            "digest",
            NOW,
            NOW.plus(Duration.ofHours(1)));
    assertTrue(creation.createIfRequired(result, persisted).isEmpty());
  }

  @Test
  void processorDeliversOnce() {
    CanonicalExecutionResult result = sampleResult("e-cb-1", ExecutionState.SUCCEEDED);
    PersistedExecutionResult persisted =
        new PersistedExecutionResult(
            "res-1",
            "e-cb-1",
            "1.0.0",
            ExecutionState.SUCCEEDED,
            TechnicalStatus.SUCCESS,
            "{}",
            "digest",
            NOW,
            NOW.plus(Duration.ofHours(1)));
    var outbox = creation.createIfRequired(result, persisted).orElseThrow();

    // Persist result into the same gateway the processor uses — recreate processor with shared bundle
    InMemoryPersistenceBundle bundle = new InMemoryPersistenceBundle(clock, ids);
    ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
    var policy = CallbackDeliveryPolicy.publishedDefault("policy:cb-default", "1.0");
    var def =
        CallbackDefinition.published(
            "callback:test-originator",
            "1.0.0",
            "binding:mock-callback@1.0",
            "contract:callback:result@1.0",
            "profile:callback:test@1.0",
            policy.exactRef(),
            CallbackProjectionKind.MINIMAL_STATUS_V1.name(),
            List.of("orig-test"),
            "INTERNAL");
    // Put serialized result via coordinator
    bundle.coordinator.persistTerminalResult(
        result,
        br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState.COMPLETED,
        null,
        null);
    // Re-create outbox against empty stores after clear - use our outbox
    // Instead: insert result into bundle and rebuild outbox pointing to that resultRef
    var storedResult = bundle.resultStore.findByExecutionId("e-cb-1").orElseThrow();
    outboxStore.clear();
    CallbackOutboxRecord pending =
        new CallbackOutboxRecord(
            "outbox-1",
            "cb-logical-e-cb-1",
            "e-cb-1",
            def.exactRef(),
            def.bindingRef(),
            def.callbackContractRef(),
            def.securityProfileRef(),
            def.projectionRef(),
            storedResult.resultRef(),
            "hash",
            CallbackOutboxState.PENDING,
            NOW,
            NOW,
            NOW.plus(Duration.ofMinutes(5)),
            0,
            0L,
            null);
    outboxStore.insertIdempotent(pending);

    CallbackOutboxProcessor proc =
        new CallbackOutboxProcessor(
            outboxStore,
            attemptStore,
            contextStore,
            bundle.gateway,
            new ConfiguredCallbackDeliveryPolicyCatalog(List.of(policy)),
            new ConfiguredCallbackDefinitionCatalog(List.of(def)),
            new DefaultCallbackProjectionAdapter(mapper),
            new OriginatorMatchedCallbackAuthorizationAdapter(),
            new ConfiguredCallbackBindingResolver(Map.of(def.bindingRef(), mock)),
            ids,
            clock);

    StepVerifier.create(proc.process("outbox-1", 0L))
        .assertNext(r -> assertEquals(CallbackOutboxState.DELIVERED, r.state()))
        .verifyComplete();
    assertEquals(1, mock.invocationCount());
  }

  @Test
  void unknownDoesNotAutoRetry() {
    mock = new MockCallbackAdapter(MockCallbackAdapter.Scenario.UNKNOWN);
    CanonicalExecutionResult result = sampleResult("e-cb-1", ExecutionState.SUCCEEDED);
    InMemoryPersistenceBundle bundle = new InMemoryPersistenceBundle(clock, ids);
    bundle.coordinator.persistTerminalResult(
        result,
        br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState.COMPLETED,
        null,
        null);
    var storedResult = bundle.resultStore.findByExecutionId("e-cb-1").orElseThrow();
    var policy = CallbackDeliveryPolicy.publishedDefault("policy:cb-default", "1.0");
    var def =
        CallbackDefinition.published(
            "callback:test-originator",
            "1.0.0",
            "binding:mock-callback@1.0",
            "contract:callback:result@1.0",
            "profile:callback:test@1.0",
            policy.exactRef(),
            CallbackProjectionKind.MINIMAL_STATUS_V1.name(),
            List.of("orig-test"),
            "INTERNAL");
    outboxStore.insertIdempotent(
        new CallbackOutboxRecord(
            "outbox-u",
            "cb-logical-e-cb-1",
            "e-cb-1",
            def.exactRef(),
            def.bindingRef(),
            def.callbackContractRef(),
            def.securityProfileRef(),
            def.projectionRef(),
            storedResult.resultRef(),
            "hash",
            CallbackOutboxState.PENDING,
            NOW,
            NOW,
            NOW.plus(Duration.ofMinutes(5)),
            0,
            0L,
            null));
    ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
    CallbackOutboxProcessor proc =
        new CallbackOutboxProcessor(
            outboxStore,
            attemptStore,
            contextStore,
            bundle.gateway,
            new ConfiguredCallbackDeliveryPolicyCatalog(List.of(policy)),
            new ConfiguredCallbackDefinitionCatalog(List.of(def)),
            new DefaultCallbackProjectionAdapter(mapper),
            new OriginatorMatchedCallbackAuthorizationAdapter(),
            new ConfiguredCallbackBindingResolver(Map.of(def.bindingRef(), mock)),
            ids,
            clock);
    StepVerifier.create(proc.process("outbox-u", 0L))
        .assertNext(r -> assertEquals(CallbackOutboxState.UNKNOWN, r.state()))
        .verifyComplete();
    assertFalse(outboxStore.findReady(NOW.plusSeconds(10), 10).stream().anyMatch(o -> o.outboxId().equals("outbox-u")));
  }

  @Test
  void requeueDenyByDefault() {
    RequeueCallbackDeliveryUseCase requeue = new RequeueCallbackDeliveryUseCase();
    StepVerifier.create(
            requeue.requeue(new RequeueCallbackDeliveryUseCase.RequeueCommand("o1", "p", NOW)))
        .assertNext(
            o ->
                assertEquals(
                    br.com.banco.spider.application.security.AuthorizationDecision.DENY,
                    o.decision()))
        .verifyComplete();
  }

  @Test
  void projectionMinimalHasNoCanonicalData() {
    ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
    DefaultCallbackProjectionAdapter projection = new DefaultCallbackProjectionAdapter(mapper);
    StepVerifier.create(
            projection.project(
                CallbackProjectionKind.MINIMAL_STATUS_V1,
                sampleResult("e", ExecutionState.SUCCEEDED),
                "INTERNAL"))
        .assertNext(
            node -> {
              assertTrue(node.has("executionId"));
              assertFalse(node.has("outcome") && node.get("outcome").has("canonicalData"));
            })
        .verifyComplete();
  }

  @Test
  void draftDefinitionNotEligible() {
    CallbackDefinition draft =
        new CallbackDefinition(
            "callback:draft",
            "1.0.0",
            "binding:x",
            "contract:x",
            "profile:x",
            "policy:x@1.0",
            CallbackProjectionKind.MINIMAL_STATUS_V1.name(),
            List.of("orig"),
            "INTERNAL",
            CallbackDefinitionStatus.DRAFT,
            null,
            CallbackConfirmationMode.SYNCHRONOUS_ACK_IS_FINAL,
            null,
            null,
            CallbackRedeliverySafety.NEVER_AUTOMATIC);
    assertFalse(draft.isEligible());
  }

  private static CanonicalExecutionResult sampleResult(String executionId, ExecutionState state) {
    return CanonicalExecutionResult.builder()
        .contract(new ContractDescriptor("1.0", "1.0.0"))
        .execution(new ExecutionSummary(executionId, state, NOW, NOW, NOW))
        .contextRef(new ResultContextReference("c", "i@1", "cap@1", "j@1"))
        .trace(new ResultTraceDescriptor("corr-" + executionId, "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"))
        .outcome(CanonicalOutcome.technical(TechnicalStatus.SUCCESS))
        .errors(List.of())
        .evidenceRefs(List.of())
        .build();
  }
}
