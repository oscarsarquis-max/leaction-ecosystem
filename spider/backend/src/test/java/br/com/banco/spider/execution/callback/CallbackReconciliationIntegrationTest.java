package br.com.banco.spider.execution.callback;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.contract.ContractDescriptor;
import br.com.banco.spider.canonical.contract.ResultContextReference;
import br.com.banco.spider.canonical.contract.ResultTraceDescriptor;
import br.com.banco.spider.execution.callback.delivery.MockCallbackAdapter;
import br.com.banco.spider.execution.callback.delivery.MockCallbackDeliveryStatusQueryAdapter;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.ExecutionSummary;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import br.com.banco.spider.execution.persistence.support.InMemoryPersistenceBundle;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackDeliveryAttemptStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackOutboxStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackReconciliationAttemptStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackReconciliationStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionCallbackContextStore;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class CallbackReconciliationIntegrationTest {

  private static final Instant NOW = Instant.parse("2026-08-21T15:00:00Z");

  private SpiderClock clock;
  private IdentifierGenerator ids;
  private InMemoryCallbackOutboxStore outboxStore;
  private InMemoryCallbackDeliveryAttemptStore attemptStore;
  private InMemoryExecutionCallbackContextStore contextStore;
  private InMemoryCallbackReconciliationStore reconciliationStore;
  private InMemoryCallbackReconciliationAttemptStore reconciliationAttempts;
  private CallbackReconciliationPolicy policy;
  private CallbackDefinition def;
  private CallbackReconciliationCreationService creation;
  private CallbackReconciliationProcessor processor;
  private MockCallbackDeliveryStatusQueryAdapter statusMock;
  private MockCallbackAdapter deliveryMock;
  private CallbackOutboxProcessor outboxProcessor;

  @BeforeEach
  void setUp() {
    clock = SpiderClock.fixed(NOW);
    AtomicLong seq = new AtomicLong();
    ids = IdentifierGenerator.fixed(() -> String.valueOf(seq.incrementAndGet()));
    outboxStore = new InMemoryCallbackOutboxStore();
    attemptStore = new InMemoryCallbackDeliveryAttemptStore();
    contextStore = new InMemoryExecutionCallbackContextStore();
    reconciliationStore = new InMemoryCallbackReconciliationStore();
    reconciliationAttempts = new InMemoryCallbackReconciliationAttemptStore();
    policy = CallbackReconciliationPolicy.publishedDefault("policy:reconcile", "1.0");
    var deliveryPolicy = CallbackDeliveryPolicy.publishedDefault("policy:cb-default", "1.0");
    def =
        CallbackDefinition.published(
            "callback:test-originator",
            "1.0.0",
            "binding:mock-callback@1.0",
            "contract:callback:result@1.0",
            "profile:callback:test@1.0",
            deliveryPolicy.exactRef(),
            CallbackProjectionKind.MINIMAL_STATUS_V1.name(),
            List.of("orig-test"),
            "INTERNAL",
            CallbackConfirmationMode.STATUS_QUERY_WHEN_UNCERTAIN,
            "binding:mock-status-query@1.0",
            policy.exactRef(),
            CallbackRedeliverySafety.NEVER_AUTOMATIC);
    statusMock =
        new MockCallbackDeliveryStatusQueryAdapter(
            MockCallbackDeliveryStatusQueryAdapter.Scenario.CONFIRMED_DELIVERED, clock);
    deliveryMock = new MockCallbackAdapter(MockCallbackAdapter.Scenario.UNKNOWN);
    creation =
        new CallbackReconciliationCreationService(
            reconciliationStore,
            new ConfiguredCallbackReconciliationPolicyCatalog(List.of(policy)),
            ids,
            clock);
    processor =
        new CallbackReconciliationProcessor(
            reconciliationStore,
            reconciliationAttempts,
            contextStore,
            outboxStore,
            new ConfiguredCallbackReconciliationPolicyCatalog(List.of(policy)),
            new ConfiguredCallbackStatusQueryBindingResolver(
                Map.of("binding:mock-status-query@1.0", statusMock)),
            new CallbackRedeliveryDecisionService(),
            ids,
            clock,
            Duration.ofSeconds(30));
    InMemoryPersistenceBundle bundle = new InMemoryPersistenceBundle(clock, ids);
    ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
    outboxProcessor =
        new CallbackOutboxProcessor(
            outboxStore,
            attemptStore,
            contextStore,
            bundle.gateway,
            new ConfiguredCallbackDeliveryPolicyCatalog(List.of(deliveryPolicy)),
            new ConfiguredCallbackDefinitionCatalog(List.of(def)),
            new DefaultCallbackProjectionAdapter(mapper),
            new OriginatorMatchedCallbackAuthorizationAdapter(),
            new ConfiguredCallbackBindingResolver(Map.of(def.bindingRef(), deliveryMock)),
            creation,
            ids,
            clock);
    contextStore.insert(
        new ExecutionCallbackContext(
            "e-rec-1",
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
            new Sha256IdempotencyKeyHash().hash("cb:e-rec-1:" + def.exactRef())));
  }

  @Test
  void invalidPolicyRejected() {
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new CallbackReconciliationPolicy(
                "bad",
                "1",
                Duration.ofMillis(1),
                0,
                Duration.ofMillis(1),
                2,
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                Duration.ofMinutes(1),
                Duration.ofMillis(1),
                true,
                true,
                false,
                CallbackDefinitionStatus.PUBLISHED));
  }

  @Test
  void publishedWithoutQueryBindingRejectedWhenRequired() {
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CallbackDefinition.published(
                "callback:bad",
                "1.0.0",
                "binding:x",
                "contract:x",
                "profile:x",
                "policy:x@1",
                CallbackProjectionKind.MINIMAL_STATUS_V1.name(),
                List.of(),
                "INTERNAL",
                CallbackConfirmationMode.STATUS_QUERY_REQUIRED,
                null,
                null,
                CallbackRedeliverySafety.NEVER_AUTOMATIC));
  }

  @Test
  void unknownCreatesReconciliationAndStatusQueryConfirmsWithoutRedispatch() {
    InMemoryPersistenceBundle bundle = new InMemoryPersistenceBundle(clock, ids);
    CanonicalExecutionResult result =
        CanonicalExecutionResult.builder()
            .contract(new ContractDescriptor("1.0", "1.0.0"))
            .execution(new ExecutionSummary("e-rec-1", ExecutionState.SUCCEEDED, NOW, NOW, NOW))
            .contextRef(new ResultContextReference("c", "i@1", "cap@1", "j@1"))
            .trace(
                new ResultTraceDescriptor(
                    "corr-e-rec-1",
                    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"))
            .outcome(CanonicalOutcome.technical(TechnicalStatus.SUCCESS))
            .errors(List.of())
            .evidenceRefs(List.of())
            .build();
    bundle.coordinator.persistTerminalResult(
        result,
        br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState.COMPLETED,
        null,
        null);
    var storedResult = bundle.resultStore.findByExecutionId("e-rec-1").orElseThrow();
    ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
    var deliveryPolicy = CallbackDeliveryPolicy.publishedDefault("policy:cb-default", "1.0");
    outboxProcessor =
        new CallbackOutboxProcessor(
            outboxStore,
            attemptStore,
            contextStore,
            bundle.gateway,
            new ConfiguredCallbackDeliveryPolicyCatalog(List.of(deliveryPolicy)),
            new ConfiguredCallbackDefinitionCatalog(List.of(def)),
            new DefaultCallbackProjectionAdapter(mapper),
            new OriginatorMatchedCallbackAuthorizationAdapter(),
            new ConfiguredCallbackBindingResolver(Map.of(def.bindingRef(), deliveryMock)),
            creation,
            ids,
            clock);
    outboxStore.insertIdempotent(
        new CallbackOutboxRecord(
            "outbox-r1",
            "logical-r1",
            "e-rec-1",
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

    StepVerifier.create(outboxProcessor.process("outbox-r1", 0L))
        .assertNext(r -> assertEquals(CallbackOutboxState.UNKNOWN, r.state()))
        .verifyComplete();
    assertEquals(1, deliveryMock.invocationCount());
    assertTrue(reconciliationStore.findByOutboxId("outbox-r1").isPresent());

    Instant due = NOW.plus(policy.initialDelay());
    processor =
        new CallbackReconciliationProcessor(
            reconciliationStore,
            reconciliationAttempts,
            contextStore,
            outboxStore,
            new ConfiguredCallbackReconciliationPolicyCatalog(List.of(policy)),
            new ConfiguredCallbackStatusQueryBindingResolver(
                Map.of("binding:mock-status-query@1.0", statusMock)),
            new CallbackRedeliveryDecisionService(),
            ids,
            SpiderClock.fixed(due),
            Duration.ofSeconds(30));

    StepVerifier.create(processor.processDue("worker-a", due, 10))
        .assertNext(batch -> assertEquals(1, batch.confirmed()))
        .verifyComplete();
    assertEquals(1, statusMock.totalQueries());
    assertEquals(1, deliveryMock.invocationCount()); // no redispatch
    assertEquals(
        CallbackReconciliationState.CONFIRMED_DELIVERED,
        reconciliationStore.findByOutboxId("outbox-r1").orElseThrow().state());
    assertEquals(
        CallbackOutboxState.DELIVERED, outboxStore.findByOutboxId("outbox-r1").orElseThrow().state());
  }

  @Test
  void neverAutomaticDoesNotRedispatchAfterConfirmedAbsence() {
    CallbackRedeliveryDecisionService decisions = new CallbackRedeliveryDecisionService();
    CallbackReconciliationRecord rec =
        new CallbackReconciliationRecord(
            "crec-1",
            "outbox-x",
            "e-rec-1",
            "hash",
            policy.exactRef(),
            CallbackReconciliationState.QUERYING,
            1,
            NOW,
            NOW.minus(Duration.ofSeconds(1)),
            NOW.plus(Duration.ofMinutes(5)),
            CallbackDeliveryStatusDisposition.CONFIRMED_NOT_FOUND,
            null,
            "w",
            NOW.plus(Duration.ofSeconds(30)),
            1L,
            NOW,
            NOW);
    ExecutionCallbackContext ctx = contextStore.findByExecutionId("e-rec-1").orElseThrow();
    assertEquals(
        CallbackRedeliveryDecision.MANUAL_REVIEW_REQUIRED,
        decisions.decide(
            CallbackDeliveryStatusDisposition.CONFIRMED_NOT_FOUND,
            ctx,
            policy,
            rec,
            NOW.plus(Duration.ofSeconds(2))));
  }

  @Test
  void concurrentClaimOnlyOneWins() {
    CallbackReconciliationRecord created =
        reconciliationStore.insertIdempotent(
            new CallbackReconciliationRecord(
                "crec-c",
                "outbox-c",
                "e-rec-1",
                "hash",
                policy.exactRef(),
                CallbackReconciliationState.PENDING,
                0,
                NOW,
                NOW,
                NOW.plus(Duration.ofMinutes(5)),
                null,
                null,
                null,
                null,
                0L,
                NOW,
                NOW));
    Optional<CallbackReconciliationRecord> a =
        reconciliationStore.claim(
            created.reconciliationId(),
            created.version(),
            "worker-1",
            NOW.plus(Duration.ofSeconds(30)),
            NOW);
    Optional<CallbackReconciliationRecord> b =
        reconciliationStore.claim(
            created.reconciliationId(),
            created.version(),
            "worker-2",
            NOW.plus(Duration.ofSeconds(30)),
            NOW);
    assertTrue(a.isPresent());
    assertTrue(b.isEmpty());
  }

  @Test
  void acceptedThenDeliveredUsesMultipleQueriesWithoutSleep() {
    statusMock =
        new MockCallbackDeliveryStatusQueryAdapter(
            MockCallbackDeliveryStatusQueryAdapter.Scenario.ACCEPTED_THEN_DELIVERED, clock);
    processor =
        new CallbackReconciliationProcessor(
            reconciliationStore,
            reconciliationAttempts,
            contextStore,
            outboxStore,
            new ConfiguredCallbackReconciliationPolicyCatalog(List.of(policy)),
            new ConfiguredCallbackStatusQueryBindingResolver(
                Map.of("binding:mock-status-query@1.0", statusMock)),
            new CallbackRedeliveryDecisionService(),
            ids,
            clock,
            Duration.ofSeconds(30));
    reconciliationStore.insertIdempotent(
        new CallbackReconciliationRecord(
            "crec-a",
            "outbox-a",
            "e-rec-1",
            "hash",
            policy.exactRef(),
            CallbackReconciliationState.PENDING,
            0,
            NOW,
            NOW,
            NOW.plus(Duration.ofMinutes(5)),
            null,
            null,
            null,
            null,
            0L,
            NOW,
            NOW));
    outboxStore.insertIdempotent(
        new CallbackOutboxRecord(
            "outbox-a",
            "logical-a",
            "e-rec-1",
            def.exactRef(),
            def.bindingRef(),
            def.callbackContractRef(),
            def.securityProfileRef(),
            def.projectionRef(),
            "res",
            "hash",
            CallbackOutboxState.UNKNOWN,
            NOW,
            NOW,
            NOW.plus(Duration.ofMinutes(5)),
            1,
            0L,
            "UNKNOWN"));

    StepVerifier.create(processor.processDue("w1", NOW, 5))
        .assertNext(b -> assertEquals(1, b.retried()))
        .verifyComplete();
    CallbackReconciliationRecord mid = reconciliationStore.findByOutboxId("outbox-a").orElseThrow();
    Instant next = mid.nextQueryAt();
    processor =
        new CallbackReconciliationProcessor(
            reconciliationStore,
            reconciliationAttempts,
            contextStore,
            outboxStore,
            new ConfiguredCallbackReconciliationPolicyCatalog(List.of(policy)),
            new ConfiguredCallbackStatusQueryBindingResolver(
                Map.of("binding:mock-status-query@1.0", statusMock)),
            new CallbackRedeliveryDecisionService(),
            ids,
            SpiderClock.fixed(next),
            Duration.ofSeconds(30));
    StepVerifier.create(processor.processDue("w1", next, 5))
        .assertNext(b -> assertEquals(1, b.confirmed()))
        .verifyComplete();
    assertEquals(2, statusMock.totalQueries());
  }

  @Test
  void syncAckFinalDoesNotCreateReconciliation() {
    CallbackDefinition sync =
        CallbackDefinition.published(
            "callback:sync",
            "1.0.0",
            "binding:mock-callback@1.0",
            "contract:callback:result@1.0",
            "profile:callback:test@1.0",
            "policy:cb-default@1.0",
            CallbackProjectionKind.MINIMAL_STATUS_V1.name(),
            List.of("orig-test"),
            "INTERNAL");
    ExecutionCallbackContext ctx =
        new ExecutionCallbackContext(
            "e-sync",
            sync.exactRef(),
            sync.bindingRef(),
            sync.callbackContractRef(),
            sync.securityProfileRef(),
            sync.deliveryPolicyRef(),
            sync.projectionRef(),
            "orig-test",
            sync.integrityRef(),
            NOW,
            sync.confirmationMode(),
            sync.statusQueryBindingRef(),
            sync.reconciliationPolicyRef(),
            sync.redeliverySafety(),
            "hash-sync");
    CallbackOutboxRecord outbox =
        new CallbackOutboxRecord(
            "outbox-sync",
            "logical-sync",
            "e-sync",
            sync.exactRef(),
            sync.bindingRef(),
            sync.callbackContractRef(),
            sync.securityProfileRef(),
            sync.projectionRef(),
            "res",
            "hash",
            CallbackOutboxState.DELIVERED,
            NOW,
            NOW,
            NOW.plus(Duration.ofMinutes(5)),
            1,
            1L,
            null);
    Optional<CallbackReconciliationRecord> created =
        creation.createIfRequired(
            outbox, ctx, CallbackDeliveryResult.delivered(NOW));
    assertTrue(created.isEmpty());
  }
}
