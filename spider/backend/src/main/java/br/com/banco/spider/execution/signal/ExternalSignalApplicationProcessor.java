package br.com.banco.spider.execution.signal;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.InboxStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.governance.GovernedEffectType;
import br.com.banco.spider.governance.GovernedRuntimeSupport;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@Service
public class ExternalSignalApplicationProcessor {

  private static final Logger log =
      LoggerFactory.getLogger(ExternalSignalApplicationProcessor.class);

  public record SignalApplicationBatchResult(int claimed, int applied, int retried, int manual) {}

  private final InboxStorePort inboxStore;
  private final ExecutionWaitStorePort waitStore;
  private final ExecutionResumeService resumeService;
  private final VerifiedSignalEnvelopeStore envelopeStore;
  private final ObjectProvider<br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeStorePort>
      protectedStore;
  private final ObjectProvider<br.com.banco.spider.security.dataprotection.ProtectedPayloadService>
      protectedPayloadService;
  private final ObjectProvider<br.com.banco.spider.execution.signal.protection.VerifiedSignalEnvelopeCodec>
      envelopeCodec;
  private final ObjectProvider<br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort>
      fixationStore;
  private final ObjectProvider<br.com.banco.spider.governance.port.GovernanceSnapshotStorePort>
      snapshotStore;
  private final ObjectProvider<GovernedRuntimeSupport> governedRuntime;
  private final SpiderClock clock;
  private final int batchSize;
  private final Duration leaseDuration;
  private final int maxAttempts;

  public ExternalSignalApplicationProcessor(
      InboxStorePort inboxStore,
      ExecutionWaitStorePort waitStore,
      ExecutionResumeService resumeService,
      VerifiedSignalEnvelopeStore envelopeStore,
      ObjectProvider<br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeStorePort>
          protectedStore,
      ObjectProvider<br.com.banco.spider.security.dataprotection.ProtectedPayloadService>
          protectedPayloadService,
      ObjectProvider<br.com.banco.spider.execution.signal.protection.VerifiedSignalEnvelopeCodec>
          envelopeCodec,
      ObjectProvider<br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort>
          fixationStore,
      ObjectProvider<br.com.banco.spider.governance.port.GovernanceSnapshotStorePort> snapshotStore,
      ObjectProvider<GovernedRuntimeSupport> governedRuntime,
      SpiderClock clock,
      @Value("${spider.signal.application.batch-size:25}") int batchSize,
      @Value("${spider.signal.application.lease-duration:PT30S}") Duration leaseDuration,
      @Value("${spider.signal.application.max-attempts:5}") int maxAttempts) {
    this.inboxStore = inboxStore;
    this.waitStore = waitStore;
    this.resumeService = resumeService;
    this.envelopeStore = envelopeStore;
    this.protectedStore = protectedStore;
    this.protectedPayloadService = protectedPayloadService;
    this.envelopeCodec = envelopeCodec;
    this.fixationStore = fixationStore;
    this.snapshotStore = snapshotStore;
    this.governedRuntime = governedRuntime;
    this.clock = clock;
    this.batchSize = Math.max(1, Math.min(batchSize, 100));
    this.leaseDuration = leaseDuration == null ? Duration.ofSeconds(30) : leaseDuration;
    this.maxAttempts = Math.max(1, maxAttempts);
  }

  public Mono<SignalApplicationBatchResult> processPending(
      String workerId, Instant now, int requestedBatch) {
    int limit = Math.min(batchSize, Math.max(1, requestedBatch));
    List<InboxRecord> due = inboxStore.findDueForApplication(now, limit);
    return Flux.fromIterable(due)
        .concatMap(r -> processOne(workerId, r, now))
        .collectList()
        .map(
            outcomes -> {
              int claimed = outcomes.size();
              int applied = (int) outcomes.stream().filter(o -> o == Outcome.APPLIED).count();
              int retried = (int) outcomes.stream().filter(o -> o == Outcome.RETRIED).count();
              int manual = (int) outcomes.stream().filter(o -> o == Outcome.MANUAL).count();
              return new SignalApplicationBatchResult(claimed, applied, retried, manual);
            });
  }

  private enum Outcome {
    APPLIED,
    RETRIED,
    MANUAL,
    SKIPPED
  }

  private Mono<Outcome> processOne(String workerId, InboxRecord candidate, Instant now) {
    return Mono.fromCallable(
            () ->
                inboxStore.claimForApplication(
                    candidate.sourceRef(),
                    candidate.messageId(),
                    candidate.version(),
                    workerId,
                    now.plus(leaseDuration),
                    now))
        .flatMap(
            claimedOpt -> {
              if (claimedOpt.isEmpty()) {
                return Mono.just(Outcome.SKIPPED);
              }
              InboxRecord claimed = claimedOpt.get();
              log.info("event=inbox_claimed reasonCode=APPLYING");
              if (claimed.applicationAttemptCount() > maxAttempts) {
                return markManual(claimed, now, "MAX_ATTEMPTS");
              }
              GovernedRuntimeSupport support = governedRuntime.getIfAvailable();
              Mono<Boolean> allowed =
                  support == null
                      ? Mono.just(true)
                      : support
                          .resolveForExecution(
                              claimed.executionId(), GovernedEffectType.SIGNAL_APPLICATION)
                          .map(r -> !r.blocksExternalEffect())
                          .onErrorReturn(false);
              return allowed.flatMap(
                  ok -> {
                    if (!ok) {
                      return markManual(claimed, now, "GOVERNANCE_BLOCKED");
                    }
                    ExecutionWaitRecord wait =
                        resolveWait(claimed).orElse(null);
                    if (wait == null) {
                      return markManual(claimed, now, "WAIT_MISSING");
                    }
                    if (wait.state() == WaitState.RESUMED || wait.state() == WaitState.EXPIRED) {
                      finalizeApplied(claimed, now, "ALREADY_RESUMED");
                      log.info("event=resume_idempotent reasonCode=ALREADY");
                      return Mono.just(Outcome.APPLIED);
                    }
                    ExternalSignalEnvelope envelope =
                        envelopeStore.get(claimed.payloadRef()).orElse(null);
                    if (envelope != null) {
                      return resumeAndFinalize(claimed, wait, envelope, now);
                    }
                    return loadProtectedEnvelope(claimed, wait, now)
                        .flatMap(
                            envOpt -> {
                              if (envOpt.isEmpty()) {
                                return markManual(claimed, now, "PAYLOAD_UNAVAILABLE");
                              }
                              return resumeAndFinalize(claimed, wait, envOpt.get(), now);
                            });
                  });
            });
  }

  private Mono<Outcome> resumeAndFinalize(
      InboxRecord claimed,
      ExecutionWaitRecord wait,
      ExternalSignalEnvelope envelope,
      Instant now) {
    return resumeService
        .applySignalAndResume(envelope, wait)
        .map(
            resume -> {
              finalizeApplied(claimed, now, "APPLIED");
              envelopeStore.remove(claimed.payloadRef());
              markProtectedConsumed(claimed.payloadRef(), now);
              log.info("event=inbox_applied reasonCode=OK");
              return Outcome.APPLIED;
            })
        .onErrorResume(
            ex -> {
              Instant next = now.plus(Duration.ofSeconds(5));
              inboxStore.updateApplicationState(
                  claimed.sourceRef(),
                  claimed.messageId(),
                  claimed.version(),
                  InboxProcessingState.APPLY_PENDING,
                  null,
                  null,
                  next,
                  claimed.applicationAttemptCount(),
                  "RETRYABLE",
                  null,
                  now);
              log.info("event=inbox_retry reasonCode=RETRYABLE");
              return Mono.just(Outcome.RETRIED);
            });
  }

  private Mono<java.util.Optional<ExternalSignalEnvelope>> loadProtectedEnvelope(
      InboxRecord claimed, ExecutionWaitRecord wait, Instant now) {
    var store = protectedStore.getIfAvailable();
    var protect = protectedPayloadService.getIfAvailable();
    var codec = envelopeCodec.getIfAvailable();
    if (store == null || protect == null || codec == null) {
      return Mono.just(java.util.Optional.empty());
    }
    return Mono.fromCallable(() -> store.findByInboxLogicalKey(claimed.payloadRef()))
        .flatMap(
            envOpt -> {
              if (envOpt.isEmpty()) {
                return Mono.just(java.util.Optional.<ExternalSignalEnvelope>empty());
              }
              var protectedEnv = envOpt.get();
              var claimedEnv =
                  store
                      .claim(
                          protectedEnv.inboxLogicalKey(),
                          protectedEnv.optimisticVersion(),
                          "processor",
                          now.plus(leaseDuration),
                          now)
                      .orElse(protectedEnv);
              var profileOpt = resolveHistoricalProfile(wait, claimedEnv.dataProtectionProfileRef());
              if (profileOpt.isEmpty()) {
                log.info("event=dp_profile_missing reasonCode=HISTORICAL");
                return Mono.just(java.util.Optional.<ExternalSignalEnvelope>empty());
              }
              var profile = profileOpt.get();
              if (!profile.canDecryptWith(claimedEnv.keyVersion())) {
                log.info("event=key_version_not_accepted reasonCode=REVOKED_OR_UNKNOWN");
                store.updateState(
                    claimedEnv.inboxLogicalKey(),
                    claimedEnv.optimisticVersion(),
                    br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState
                        .QUARANTINED,
                    null,
                    null,
                    null,
                    null);
                return Mono.just(java.util.Optional.empty());
              }
              var ctx =
                  new br.com.banco.spider.security.dataprotection.ProtectedPayloadService
                      .DataProtectionContext(
                      profile,
                      claimed.payloadRef(),
                      wait.executionId(),
                      wait.waitId(),
                      claimed.signalDefinitionRef(),
                      "VERIFIED_SIGNAL_ENVELOPE_V1",
                      claimedEnv.createdAt());
              var payload =
                  new br.com.banco.spider.security.dataprotection.ProtectedPayloadService
                      .ProtectedPayload(
                      claimedEnv.algorithm(),
                      claimedEnv.keyRef(),
                      claimedEnv.keyVersion(),
                      claimedEnv.aadVersion(),
                      claimedEnv.iv(),
                      claimedEnv.ciphertextAndTag(),
                      claimedEnv.plaintextSize());
              return protect
                  .unprotect(payload, ctx)
                  .map(
                      plaintext -> {
                        try {
                          var canonical = codec.decode(plaintext);
                          ExternalSignalEnvelope rebuilt =
                              rebuildEnvelope(canonical, claimed, wait);
                          java.util.Arrays.fill(plaintext, (byte) 0);
                          log.info("event=envelope_decrypted reasonCode=OK");
                          return java.util.Optional.of(rebuilt);
                        } catch (Exception ex) {
                          store.updateState(
                              claimedEnv.inboxLogicalKey(),
                              claimedEnv.optimisticVersion(),
                              br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState
                                  .CORRUPT,
                              null,
                              null,
                              null,
                              null);
                          log.info("event=envelope_corrupt reasonCode=CODEC_OR_TAG");
                          return java.util.Optional.<ExternalSignalEnvelope>empty();
                        }
                      })
                  .onErrorResume(
                      ex -> {
                        String msg = ex.getMessage() == null ? "" : ex.getMessage();
                        if (msg.contains("KEY_UNAVAILABLE") || msg.contains("KEY_PROVIDER")) {
                          store.updateState(
                              claimedEnv.inboxLogicalKey(),
                              claimedEnv.optimisticVersion(),
                              br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState
                                  .KEY_UNAVAILABLE,
                              null,
                              null,
                              null,
                              null);
                          log.info("event=key_unavailable reasonCode=RETRY");
                        } else {
                          store.updateState(
                              claimedEnv.inboxLogicalKey(),
                              claimedEnv.optimisticVersion(),
                              br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState
                                  .CORRUPT,
                              null,
                              null,
                              null,
                              null);
                          log.info("event=envelope_corrupt reasonCode=DECRYPT");
                        }
                        return Mono.just(java.util.Optional.empty());
                      });
            });
  }

  private java.util.Optional<br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition>
      resolveHistoricalProfile(ExecutionWaitRecord wait, String profileRefFromEnvelope) {
    String ref =
        wait.dataProtectionProfileRef() != null
            ? wait.dataProtectionProfileRef()
            : profileRefFromEnvelope;
    if (ref == null || ref.isBlank()) {
      return java.util.Optional.empty();
    }
    var fixStore = fixationStore.getIfAvailable();
    var snapStore = snapshotStore.getIfAvailable();
    if (fixStore == null || snapStore == null) {
      return java.util.Optional.empty();
    }
    return fixStore
        .findByExecutionId(wait.executionId())
        .flatMap(f -> snapStore.findSnapshotById(f.snapshotId()))
        .flatMap(snap -> snap.dataProtectionProfile(ref));
  }

  private ExternalSignalEnvelope rebuildEnvelope(
      br.com.banco.spider.execution.signal.protection.VerifiedSignalEnvelopeCodec
              .CanonicalVerifiedEnvelope c,
      InboxRecord claimed,
      ExecutionWaitRecord wait) {
    Instant received =
        c.receivedAt() == null ? claimed.receivedAt() : Instant.parse(c.receivedAt());
    return new ExternalSignalEnvelope(
        "1.0",
        c.messageId(),
        c.sourceRef(),
        c.bindingRef(),
        c.contractRef(),
        c.executionId() != null ? c.executionId() : wait.executionId(),
        c.stepId() != null ? c.stepId() : wait.stepId(),
        c.externalOperationRef(),
        received,
        received,
        claimed.messageId(),
        null,
        new SignalSecurityContext(
            "mock-principal",
            c.sourceRef() == null ? claimed.sourceRef() : c.sourceRef(),
            "MOCK",
            received,
            received.plusSeconds(3600),
            c.securityProfileRef() == null ? "profile:mock" : c.securityProfileRef(),
            null),
        new SignalCompletion(
            br.com.banco.spider.integration.port.AdapterDispositionMode.valueOf(c.disposition()),
            br.com.banco.spider.execution.domain.CanonicalOutcome.technical(
                br.com.banco.spider.execution.domain.TechnicalStatus.SUCCESS),
            List.of(),
            List.of()),
        null,
        null);
  }

  private void markProtectedConsumed(String payloadRef, Instant now) {
    var store = protectedStore.getIfAvailable();
    if (store == null) {
      return;
    }
    store
        .findByInboxLogicalKey(payloadRef)
        .ifPresent(
            e ->
                store.updateState(
                    e.inboxLogicalKey(),
                    e.optimisticVersion(),
                    br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState.CONSUMED,
                    null,
                    null,
                    now,
                    null));
  }

  private java.util.Optional<ExecutionWaitRecord> resolveWait(InboxRecord claimed) {
    if (claimed.waitId() != null && !claimed.waitId().isBlank()) {
      return waitStore.findByWaitId(claimed.waitId());
    }
    return waitStore.findActiveByExecutionAndStep(claimed.executionId(), claimed.stepId());
  }

  private Mono<Outcome> markManual(InboxRecord claimed, Instant now, String reason) {
    inboxStore.updateApplicationState(
        claimed.sourceRef(),
        claimed.messageId(),
        claimed.version(),
        InboxProcessingState.MANUAL_REVIEW,
        null,
        null,
        now,
        claimed.applicationAttemptCount(),
        reason,
        null,
        now);
    log.info("event=inbox_manual_review reasonCode={}", reason);
    return Mono.just(Outcome.MANUAL);
  }

  private void finalizeApplied(InboxRecord claimed, Instant now, String reason) {
    inboxStore.updateApplicationState(
        claimed.sourceRef(),
        claimed.messageId(),
        claimed.version(),
        InboxProcessingState.APPLIED,
        null,
        null,
        now,
        claimed.applicationAttemptCount(),
        reason,
        now,
        now);
  }
}
