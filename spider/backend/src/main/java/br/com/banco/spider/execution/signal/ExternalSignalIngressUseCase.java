package br.com.banco.spider.execution.signal;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.inbox.InboxReservationResult;
import br.com.banco.spider.execution.inbox.InboxReservationStatus;
import br.com.banco.spider.execution.inbox.InboxValidationState;
import br.com.banco.spider.execution.persistence.port.InboxStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.governance.GovernedEffectType;
import br.com.banco.spider.governance.GovernanceInFlightDecisionService;
import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/**
 * Ingress governado: quando durable-application=false, delega ao fluxo legado (aplica inline).
 * Quando true, verifica e persiste Inbox APPLY_PENDING sem resume.
 */
@Service
public class ExternalSignalIngressUseCase {

  private static final Logger log = LoggerFactory.getLogger(ExternalSignalIngressUseCase.class);

  private final boolean durableApplication;
  private final ExternalSignalApplicationPort legacyApplication;
  private final ExternalSignalIntegrityGate integrityGate;
  private final ExternalSignalIngressContextResolver contextResolver;
  private final InboxStorePort inboxStore;
  private final ExternalSignalFingerprintPort fingerprintPort;
  private final InboxDeduplicationKeyPort dedupKeyPort;
  private final ExternalSignalAuthorizationPort authorization;
  private final ObjectProvider<GovernanceInFlightDecisionService> decisions;
  private final VerifiedSignalEnvelopeStore envelopeStore;
  private final ObjectProvider<br.com.banco.spider.execution.signal.continuation.ContinuationTokenWaitResolver>
      tokenResolver;
  private final boolean requireTokenForDurable;
  private final boolean envelopeProtectionEnabled;
  private final ObjectProvider<br.com.banco.spider.security.dataprotection.ProtectedPayloadService>
      protectedPayloadService;
  private final ObjectProvider<br.com.banco.spider.execution.signal.protection.VerifiedSignalEnvelopeCodec>
      envelopeCodec;
  private final ObjectProvider<br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeStorePort>
      protectedStore;
  private final br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash sha256;
  private final SpiderClock clock;
  private final int maxEnvelopeBytes;
  private OperationalEventPublisher events = OperationalEventPublisher.noop();

  public ExternalSignalIngressUseCase(
      @Value("${spider.signal.ingress.durable-application.enabled:false}")
          boolean durableApplication,
      ExternalSignalApplicationPort legacyApplication,
      ExternalSignalIntegrityGate integrityGate,
      ExternalSignalIngressContextResolver contextResolver,
      InboxStorePort inboxStore,
      ExternalSignalFingerprintPort fingerprintPort,
      InboxDeduplicationKeyPort dedupKeyPort,
      ExternalSignalAuthorizationPort authorization,
      ObjectProvider<GovernanceInFlightDecisionService> decisions,
      VerifiedSignalEnvelopeStore envelopeStore,
      ObjectProvider<br.com.banco.spider.execution.signal.continuation.ContinuationTokenWaitResolver>
          tokenResolver,
      @Value("${spider.signal.continuation-token.require-for-durable:true}")
          boolean requireTokenForDurable,
      @Value("${spider.signal.envelope-protection.enabled:false}") boolean envelopeProtectionEnabled,
      ObjectProvider<br.com.banco.spider.security.dataprotection.ProtectedPayloadService>
          protectedPayloadService,
      ObjectProvider<br.com.banco.spider.execution.signal.protection.VerifiedSignalEnvelopeCodec>
          envelopeCodec,
      ObjectProvider<br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeStorePort>
          protectedStore,
      br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash sha256,
      SpiderClock clock,
      @Value("${spider.signal.max-envelope-bytes:262144}") int maxEnvelopeBytes) {
    this.durableApplication = durableApplication;
    this.legacyApplication = legacyApplication;
    this.integrityGate = integrityGate;
    this.contextResolver = contextResolver;
    this.inboxStore = inboxStore;
    this.fingerprintPort = fingerprintPort;
    this.dedupKeyPort = dedupKeyPort;
    this.authorization = authorization;
    this.decisions = decisions;
    this.envelopeStore = envelopeStore;
    this.tokenResolver = tokenResolver;
    this.requireTokenForDurable = requireTokenForDurable;
    this.envelopeProtectionEnabled = envelopeProtectionEnabled;
    this.protectedPayloadService = protectedPayloadService;
    this.envelopeCodec = envelopeCodec;
    this.protectedStore = protectedStore;
    this.sha256 = sha256;
    this.clock = clock;
    this.maxEnvelopeBytes = Math.max(1024, maxEnvelopeBytes);
  }

  @org.springframework.beans.factory.annotation.Autowired(required = false)
  void setOperationalEventPublisher(OperationalEventPublisher publisher) {
    if (publisher != null) {
      this.events = publisher;
    }
  }

  public Mono<ExternalSignalIngressResult> ingest(ExternalSignalEnvelope envelope) {
    if (envelope == null || envelope.messageId() == null || envelope.messageId().isBlank()) {
      log.info("event=signal_structurally_rejected reasonCode=MESSAGE_ID");
      return Mono.just(ExternalSignalIngressResult.of(ExternalSignalIngressOutcome.REJECTED, "STRUCTURAL"));
    }
    emitSignal(
        OperationalEventType.SIGNAL_RECEIVED,
        envelope,
        OperationalEventOutcome.INFO,
        "RECEIVED");
    Mono<ExternalSignalIngressResult> result;
    if (!durableApplication) {
      result = legacyApplication.process(envelope).map(ExternalSignalIngressResult::legacy);
    } else {
      result = ingestDurable(envelope);
    }
    return result.doOnNext(value -> emitSignalResult(envelope, value));
  }

  private void emitSignalResult(
      ExternalSignalEnvelope envelope, ExternalSignalIngressResult result) {
    OperationalEventType type =
        switch (result.outcome()) {
          case REPLAY_CONFLICT -> OperationalEventType.SECURITY_REPLAY_REJECTED;
          case INVALID_PROOF -> OperationalEventType.SECURITY_INTEGRITY_REJECTED;
          case UNAUTHORIZED -> OperationalEventType.SECURITY_TOKEN_REJECTED;
          case ACCEPTED_PENDING_APPLICATION,
              DUPLICATE_ALREADY_ACCEPTED,
              DUPLICATE_ALREADY_APPLIED,
              APPLIED_INLINE -> OperationalEventType.SIGNAL_ACCEPTED;
          default ->
              result.safeReasonCategory() != null
                      && result.safeReasonCategory().toUpperCase().contains("TOKEN")
                  ? OperationalEventType.SECURITY_TOKEN_REJECTED
                  : OperationalEventType.SIGNAL_REJECTED;
        };
    OperationalEventOutcome outcome =
        type == OperationalEventType.SIGNAL_ACCEPTED
            ? OperationalEventOutcome.SUCCESS
            : OperationalEventOutcome.REJECTED;
    emitSignal(type, envelope, outcome, result.safeReasonCategory());
  }

  private void emitSignal(
      OperationalEventType type,
      ExternalSignalEnvelope envelope,
      OperationalEventOutcome outcome,
      String reason) {
    OperationalEventEmit.publish(
        events,
        OperationalEventEmit.draft(
            type,
            envelope.executionId(),
            envelope.trace() == null ? null : envelope.trace().correlationId(),
            "signal-ingress",
            outcome,
            null,
            OperationalEventAttributes.builder()
                .reasonCode(reason)
                .signalOutcome(type.name())
                .integrityReason(
                    type.category()
                            == br.com.banco.spider.operational.events.OperationalEventCategory.SECURITY
                        ? reason
                        : null)
                .build()));
  }

  private Mono<ExternalSignalIngressResult> ingestDurable(ExternalSignalEnvelope envelope) {
    Instant now = clock.now();
    Mono<Optional<br.com.banco.spider.execution.wait.ExecutionWaitRecord>> waitMono;
    var resolver = tokenResolver.getIfAvailable();
    if (envelope.continuationToken() != null
        && !envelope.continuationToken().isBlank()
        && resolver != null) {
      waitMono = resolver.resolveByToken(envelope.continuationToken(), now);
    } else if (requireTokenForDurable) {
      log.info("event=wait_lookup_normalized_failure reasonCode=TOKEN_REQUIRED");
      return Mono.just(ExternalSignalIngressResult.of(ExternalSignalIngressOutcome.ORPHAN, "TOKEN"));
    } else {
      waitMono = contextResolver.findActiveWait(envelope.executionId(), envelope.stepId());
      log.info("event=legacy_lookup_used reasonCode=EXEC_STEP");
    }
    return waitMono.flatMap(
        waitOpt -> {
              if (waitOpt.isEmpty()) {
                log.info("event=wait_lookup_normalized_failure reasonCode=ORPHAN");
                return Mono.just(
                    ExternalSignalIngressResult.of(ExternalSignalIngressOutcome.ORPHAN, "ORPHAN"));
              }
              var wait = waitOpt.get();
              if (envelope.executionId() != null
                  && !envelope.executionId().equals(wait.executionId())) {
                log.info("event=wait_lookup_normalized_failure reasonCode=OWNERSHIP");
                return Mono.just(
                    ExternalSignalIngressResult.of(
                        ExternalSignalIngressOutcome.REJECTED, "OWNERSHIP"));
              }
              if (!wait.expiresAt().isAfter(now)) {
                log.info("event=late_orphan_normalized reasonCode=LATE");
                return Mono.just(
                    ExternalSignalIngressResult.of(ExternalSignalIngressOutcome.LATE, "LATE"));
              }
              return contextResolver
                  .resolveForWait(wait)
                  .flatMap(
                      ctxOpt -> {
                        if (ctxOpt.isPresent()) {
                          ExternalSignalIngressContext ctx = ctxOpt.get();
                          if (!ctx.expectedContractRef().equals(envelope.contractRef())
                              && !ctx.expectedContractRef().equals(wait.expectedSignalContractRef())) {
                            // claim do envelope deve coincidir com definition/wait
                            if (!envelope.contractRef().equals(wait.expectedSignalContractRef())) {
                              return Mono.just(
                                  ExternalSignalIngressResult.of(
                                      ExternalSignalIngressOutcome.CONTRACT_MISMATCH,
                                      "CONTRACT"));
                            }
                          }
                          GovernanceInFlightDecisionService dec = decisions.getIfAvailable();
                          if (dec != null
                              && !dec.allowsExternalEffect(
                                  dec.decide(
                                      ctx.governanceRef(),
                                      GovernedEffectType.SIGNAL_APPLICATION,
                                      null))) {
                            return Mono.just(
                                ExternalSignalIngressResult.of(
                                    ExternalSignalIngressOutcome.REVOKED, "REVOKED"));
                          }
                        }
                        return verifyAndPersist(envelope, wait, ctxOpt);
                      });
            });
  }

  private Mono<ExternalSignalIngressResult> verifyAndPersist(
      ExternalSignalEnvelope envelope,
      br.com.banco.spider.execution.wait.ExecutionWaitRecord wait,
      Optional<ExternalSignalIngressContext> ctxOpt) {
    Mono<ExternalSignalIntegrityGate.GateResult> gateMono =
        integrityGate == null
            ? Mono.just(new ExternalSignalIntegrityGate.GateResult(true, "SKIP", false))
            : integrityGate.evaluate(envelope, ctxOpt.orElse(null));

    return gateMono.flatMap(
        gate -> {
          if (!gate.allowed()) {
            log.info("event=integrity_rejected reasonCode={}", gate.reasonCode());
            ExternalSignalIngressOutcome outcome =
                "REPLAY_CONFLICT".equals(gate.reasonCode())
                    ? ExternalSignalIngressOutcome.REPLAY_CONFLICT
                    : ExternalSignalIngressOutcome.INVALID_PROOF;
            return Mono.just(ExternalSignalIngressResult.of(outcome, gate.reasonCode()));
          }
          if (gate.duplicateSameMessage()) {
            return Mono.just(
                ExternalSignalIngressResult.of(
                    ExternalSignalIngressOutcome.DUPLICATE_ALREADY_ACCEPTED, "REPLAY_DUP"));
          }
          return authorization
              .authorize(
                  envelope.securityContext(),
                  envelope.bindingRef(),
                  ctxOpt
                      .map(ExternalSignalIngressContext::integrityProfileRef)
                      .orElse(envelope.securityContext().securityProfileRef()))
              .flatMap(
                  authorized -> {
                    if (!authorized) {
                      return Mono.just(
                          ExternalSignalIngressResult.of(
                              ExternalSignalIngressOutcome.UNAUTHORIZED, "AUTHZ"));
                    }
                    Instant now = clock.now();
                    String fp = fingerprintPort.fingerprint(envelope);
                    String dedup =
                        dedupKeyPort.deduplicationKeyHash(
                            envelope.sourceRef(), envelope.messageId());
                    String payloadRef = "env:" + dedup;
                    Mono<Void> persistEnvelope =
                        persistVerifiedEnvelope(envelope, wait, payloadRef, now, ctxOpt);
                    InboxRecord candidate =
                        new InboxRecord(
                            envelope.messageId(),
                            envelope.sourceRef(),
                            envelope.bindingRef(),
                            envelope.contractRef(),
                            dedup,
                            fp,
                            fingerprintPort.fingerprintVersion(),
                            wait.executionId(),
                            wait.stepId(),
                            envelope.externalOperationRef(),
                            envelope.receivedAt(),
                            InboxValidationState.VALIDATED,
                            InboxProcessingState.APPLY_PENDING,
                            payloadRef,
                            null,
                            now.plus(Duration.ofHours(24)),
                            wait.waitId(),
                            ctxOpt.map(c -> c.signalDefinition().ref()).orElse(null),
                            fp,
                            0,
                            now,
                            null,
                            null,
                            0L,
                            now,
                            null);
                    return persistEnvelope.then(
                        Mono.fromCallable(() -> inboxStore.reserve(candidate))
                            .flatMap(
                                reservation ->
                                    switch (reservation.status()) {
                                      case RESERVED_NEW -> {
                                        log.info(
                                            "event=inbox_apply_pending reasonCode=ACCEPTED waitPresent=true");
                                        yield Mono.just(
                                            ExternalSignalIngressResult.of(
                                                ExternalSignalIngressOutcome
                                                    .ACCEPTED_PENDING_APPLICATION,
                                                "APPLY_PENDING"));
                                      }
                                      case DUPLICATE_SAME_SIGNAL ->
                                          Mono.just(
                                              ExternalSignalIngressResult.of(
                                                  reservation.record().processingState()
                                                          == InboxProcessingState.APPLIED
                                                      ? ExternalSignalIngressOutcome
                                                          .DUPLICATE_ALREADY_APPLIED
                                                      : ExternalSignalIngressOutcome
                                                          .DUPLICATE_ALREADY_ACCEPTED,
                                                  "INBOX_DUP"));
                                      case CONFLICTING_SIGNAL ->
                                          Mono.just(
                                              ExternalSignalIngressResult.of(
                                                  ExternalSignalIngressOutcome.REPLAY_CONFLICT,
                                                  "INBOX_CONFLICT"));
                                      case EXISTING_IN_PROGRESS ->
                                          Mono.just(
                                              ExternalSignalIngressResult.of(
                                                  ExternalSignalIngressOutcome
                                                      .DUPLICATE_ALREADY_ACCEPTED,
                                                  "IN_PROGRESS"));
                                    }));
                  });
        });
  }

  private Mono<Void> persistVerifiedEnvelope(
      ExternalSignalEnvelope envelope,
      br.com.banco.spider.execution.wait.ExecutionWaitRecord wait,
      String payloadRef,
      Instant now,
      Optional<ExternalSignalIngressContext> ctxOpt) {
    if (!envelopeProtectionEnabled) {
      envelopeStore.put(payloadRef, envelope);
      return Mono.empty();
    }
    var codec = envelopeCodec.getIfAvailable();
    var protect = protectedPayloadService.getIfAvailable();
    var store = protectedStore.getIfAvailable();
    if (codec == null || protect == null || store == null) {
      return Mono.error(new IllegalStateException("ENVELOPE_PROTECTION_UNAVAILABLE"));
    }
    byte[] plaintext = codec.encode(envelope, now);
    String plaintextDigest = sha256.hash(java.util.Base64.getEncoder().encodeToString(plaintext));
    return resolveDataProtectionProfile(wait, ctxOpt)
        .flatMap(
            profile -> {
              var ctx =
                  new br.com.banco.spider.security.dataprotection.ProtectedPayloadService
                      .DataProtectionContext(
                      profile,
                      payloadRef,
                      wait.executionId(),
                      wait.waitId(),
                      ctxOpt
                          .map(c -> c.signalDefinition().ref())
                          .orElse(wait.signalDefinitionRef()),
                      "VERIFIED_SIGNAL_ENVELOPE_V1",
                      now);
              return protect
                  .protect(plaintext, ctx)
                  .doOnNext(
                      protectedPayload -> {
                        String ctDigest =
                            sha256.hash(
                                java.util.Base64.getEncoder()
                                    .encodeToString(protectedPayload.ciphertextAndTag()));
                        store.createOnce(
                            new br.com.banco.spider.execution.signal.protection
                                .ProtectedSignalEnvelope(
                                "pse-" + payloadRef.hashCode(),
                                payloadRef,
                                profile.exactRef(),
                                protectedPayload.algorithm(),
                                protectedPayload.keyRef(),
                                protectedPayload.keyVersion(),
                                protectedPayload.aadVersion(),
                                protectedPayload.iv(),
                                protectedPayload.ciphertextAndTag(),
                                plaintextDigest,
                                ctDigest,
                                protectedPayload.plaintextSize(),
                                br.com.banco.spider.execution.signal.protection
                                    .ProtectedEnvelopeState.AVAILABLE,
                                now,
                                null,
                                null,
                                null,
                                null,
                                0L));
                        log.info("event=envelope_protected reasonCode=OK algorithm=AES_256_GCM");
                        java.util.Arrays.fill(plaintext, (byte) 0);
                      })
                  .then();
            });
  }

  private Mono<br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition>
      resolveDataProtectionProfile(
          br.com.banco.spider.execution.wait.ExecutionWaitRecord wait,
          Optional<ExternalSignalIngressContext> ctxOpt) {
    String ref = wait.dataProtectionProfileRef();
    if ((ref == null || ref.isBlank()) && ctxOpt.isPresent()) {
      ref = ctxOpt.get().signalDefinition().dataProtectionProfileRef();
    }
    if (ref == null || ref.isBlank()) {
      log.info("event=dp_profile_missing reasonCode=NO_REF");
      return Mono.error(new IllegalStateException("DATA_PROTECTION_PROFILE_REQUIRED"));
    }
    final String profileRef = ref;
    if (ctxOpt.isPresent()) {
      return Mono.justOrEmpty(
              ctxOpt
                  .get()
                  .resolutionContext()
                  .dataProtectionProfileCatalog()
                  .findPublished(profileRef))
          .switchIfEmpty(Mono.error(new IllegalStateException("DATA_PROTECTION_PROFILE_NOT_FOUND")));
    }
    return Mono.error(new IllegalStateException("DATA_PROTECTION_PROFILE_CONTEXT_REQUIRED"));
  }
}
