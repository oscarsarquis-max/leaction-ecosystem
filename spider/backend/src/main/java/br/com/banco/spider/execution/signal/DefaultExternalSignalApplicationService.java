package br.com.banco.spider.execution.signal;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.inbox.InboxReservationResult;
import br.com.banco.spider.execution.inbox.InboxReservationStatus;
import br.com.banco.spider.execution.inbox.InboxValidationState;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.InboxStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class DefaultExternalSignalApplicationService implements ExternalSignalApplicationPort {

  private static final Logger log = LoggerFactory.getLogger(DefaultExternalSignalApplicationService.class);

  private final InboxStorePort inboxStore;
  private final ExecutionWaitStorePort waitStore;
  private final ExecutionStepStorePort stepStore;
  private final ExternalSignalFingerprintPort fingerprintPort;
  private final InboxDeduplicationKeyPort dedupKeyPort;
  private final ExternalSignalAuthorizationPort authorization;
  private final ExternalSignalValidator validator;
  private final ExecutionResumeService resumeService;
  private final ExternalSignalIntegrityGate integrityGate;
  private final SpiderClock clock;

  @org.springframework.beans.factory.annotation.Autowired
  public DefaultExternalSignalApplicationService(
      InboxStorePort inboxStore,
      ExecutionWaitStorePort waitStore,
      ExecutionStepStorePort stepStore,
      ExternalSignalFingerprintPort fingerprintPort,
      InboxDeduplicationKeyPort dedupKeyPort,
      ExternalSignalAuthorizationPort authorization,
      ExternalSignalValidator validator,
      ExecutionResumeService resumeService,
      ExternalSignalIntegrityGate integrityGate,
      SpiderClock clock) {
    this.inboxStore = inboxStore;
    this.waitStore = waitStore;
    this.stepStore = stepStore;
    this.fingerprintPort = fingerprintPort;
    this.dedupKeyPort = dedupKeyPort;
    this.authorization = authorization;
    this.validator = validator;
    this.resumeService = resumeService;
    this.integrityGate = integrityGate;
    this.clock = clock;
  }

  /** Construtor de teste sem integrity gate. */
  public DefaultExternalSignalApplicationService(
      InboxStorePort inboxStore,
      ExecutionWaitStorePort waitStore,
      ExecutionStepStorePort stepStore,
      ExternalSignalFingerprintPort fingerprintPort,
      InboxDeduplicationKeyPort dedupKeyPort,
      ExternalSignalAuthorizationPort authorization,
      ExternalSignalValidator validator,
      ExecutionResumeService resumeService,
      SpiderClock clock) {
    this(
        inboxStore,
        waitStore,
        stepStore,
        fingerprintPort,
        dedupKeyPort,
        authorization,
        validator,
        resumeService,
        null,
        clock);
  }

  @Override
  public Mono<ExternalSignalProcessingResult> process(ExternalSignalEnvelope signal) {
    log.info(
        "event=signal_received sourceRef={} messageIdPresent=true executionId={}",
        signal.sourceRef(),
        signal.executionId());

    Mono<ExternalSignalIntegrityGate.GateResult> gateMono =
        integrityGate == null
            ? Mono.just(new ExternalSignalIntegrityGate.GateResult(true, "SKIP", false))
            : integrityGate.evaluate(signal);

    return gateMono.flatMap(
        gate -> {
          if (!gate.allowed()) {
            log.info("event=signal_integrity_rejected reasonCode={}", gate.reasonCode());
            return Mono.just(
                ExternalSignalProcessingResult.of(
                    ExternalSignalProcessingStatus.REJECTED,
                    signal.executionId(),
                    null,
                    null,
                    null,
                    error(gate.reasonCode(), "Integrity rejected")));
          }
          if (gate.duplicateSameMessage()) {
            log.info("event=duplicate sourceRef={} reasonCode=CRYPTO_REPLAY_DUPLICATE", signal.sourceRef());
            return Mono.just(
                ExternalSignalProcessingResult.of(
                    ExternalSignalProcessingStatus.DUPLICATE,
                    signal.executionId(),
                    null,
                    null,
                    null,
                    null));
          }
          return processAfterIntegrity(signal);
        });
  }

  private Mono<ExternalSignalProcessingResult> processAfterIntegrity(ExternalSignalEnvelope signal) {
    Instant now = clock.now();
    String fp = fingerprintPort.fingerprint(signal);
    String dedup = dedupKeyPort.deduplicationKeyHash(signal.sourceRef(), signal.messageId());
    InboxRecord candidate =
        new InboxRecord(
            signal.messageId(),
            signal.sourceRef(),
            signal.bindingRef(),
            signal.contractRef(),
            dedup,
            fp,
            fingerprintPort.fingerprintVersion(),
            signal.executionId(),
            signal.stepId(),
            signal.externalOperationRef(),
            signal.receivedAt(),
            InboxValidationState.RECEIVED,
            InboxProcessingState.PENDING,
            null,
            null,
            now.plus(Duration.ofHours(24)));

    InboxReservationResult reservation = inboxStore.reserve(candidate);
    log.info(
        "event=signal_reserved status={} sourceRef={}",
        reservation.status(),
        signal.sourceRef());

    if (reservation.status() == InboxReservationStatus.DUPLICATE_SAME_SIGNAL) {
      log.info("event=duplicate sourceRef={} reasonCode=SAME_FINGERPRINT", signal.sourceRef());
      return Mono.just(
          ExternalSignalProcessingResult.of(
              ExternalSignalProcessingStatus.DUPLICATE,
              signal.executionId(),
              null,
              null,
              null,
              null));
    }
    if (reservation.status() == InboxReservationStatus.CONFLICTING_SIGNAL) {
      log.info("event=conflict sourceRef={} reasonCode=FINGERPRINT_MISMATCH", signal.sourceRef());
      return Mono.just(
          ExternalSignalProcessingResult.of(
              ExternalSignalProcessingStatus.CONFLICT,
              signal.executionId(),
              null,
              null,
              null,
              error("SIGNAL_CONFLICT", "Conflicting signal for same messageId")));
    }
    if (reservation.status() == InboxReservationStatus.EXISTING_IN_PROGRESS) {
      log.info("event=inbox_recovery_candidate sourceRef={} reasonCode=PROCESSING", signal.sourceRef());
      return Mono.just(
          ExternalSignalProcessingResult.of(
              ExternalSignalProcessingStatus.DUPLICATE,
              signal.executionId(),
              null,
              null,
              null,
              null));
    }

    return authorization
        .authorize(signal.securityContext(), signal.bindingRef(), signal.securityContext().securityProfileRef())
        .flatMap(
            authorized -> {
              if (authorized) {
                log.info("event=signal_authorized sourceRef={}", signal.sourceRef());
                inboxStore.updateStates(
                    signal.sourceRef(),
                    signal.messageId(),
                    InboxValidationState.AUTHENTICATED,
                    InboxProcessingState.PENDING,
                    null,
                    null);
              } else {
                log.info(
                    "event=signal_rejected sourceRef={} reasonCode=UNAUTHORIZED",
                    signal.sourceRef());
                inboxStore.updateStates(
                    signal.sourceRef(),
                    signal.messageId(),
                    InboxValidationState.REJECTED,
                    InboxProcessingState.FAILED,
                    null,
                    "UNAUTHORIZED");
                return Mono.just(
                    ExternalSignalProcessingResult.of(
                        ExternalSignalProcessingStatus.REJECTED,
                        signal.executionId(),
                        null,
                        null,
                        null,
                        error("SIGNAL_UNAUTHORIZED", "Not authorized")));
              }

              ExecutionWaitRecord wait =
                  waitStore
                      .findActiveByExecutionAndStep(signal.executionId(), signal.stepId())
                      .orElse(null);

              if (wait == null) {
                var step = stepStore.find(signal.executionId(), signal.stepId());
                if (step.isPresent() && step.get().state().isTerminal()) {
                  inboxStore.updateStates(
                      signal.sourceRef(),
                      signal.messageId(),
                      InboxValidationState.VALIDATED,
                      InboxProcessingState.LATE_REJECTED,
                      null,
                      "LATE");
                  log.info(
                      "event=late_signal executionId={} reasonCode=TERMINAL_STEP",
                      signal.executionId());
                  return Mono.just(
                      ExternalSignalProcessingResult.of(
                          ExternalSignalProcessingStatus.LATE_REJECTED,
                          signal.executionId(),
                          null,
                          step.get().state(),
                          null,
                          error("SIGNAL_LATE", "Wait already resolved")));
                }

                inboxStore.updateStates(
                    signal.sourceRef(),
                    signal.messageId(),
                    InboxValidationState.VALIDATED,
                    InboxProcessingState.ORPHANED,
                    null,
                    "ORPHAN");
                log.info(
                    "event=orphan_signal sourceRef={} reasonCode=NO_WAIT",
                    signal.sourceRef());
                return Mono.just(
                    ExternalSignalProcessingResult.of(
                        ExternalSignalProcessingStatus.ORPHANED,
                        signal.executionId(),
                        null,
                        null,
                        null,
                        error("SIGNAL_ORPHAN", "No matching wait")));
              }

              if (wait.state() != WaitState.WAITING) {
                inboxStore.updateStates(
                    signal.sourceRef(),
                    signal.messageId(),
                    InboxValidationState.VALIDATED,
                    InboxProcessingState.LATE_REJECTED,
                    null,
                    "WAIT_NOT_ACTIVE");
                log.info(
                    "event=late_signal executionId={} reasonCode=WAIT_NOT_ACTIVE",
                    signal.executionId());
                return Mono.just(
                    ExternalSignalProcessingResult.of(
                        ExternalSignalProcessingStatus.LATE_REJECTED,
                        signal.executionId(),
                        null,
                        null,
                        null,
                        error("SIGNAL_LATE", "Wait not active")));
              }

              List<CanonicalError> validationErrors =
                  validator.validate(signal, wait, true);
              if (!validationErrors.isEmpty()) {
                inboxStore.updateStates(
                    signal.sourceRef(),
                    signal.messageId(),
                    InboxValidationState.REJECTED,
                    InboxProcessingState.FAILED,
                    null,
                    validationErrors.getFirst().code());
                log.info(
                    "event=signal_rejected sourceRef={} reasonCode={}",
                    signal.sourceRef(),
                    validationErrors.getFirst().code());
                return Mono.just(
                    ExternalSignalProcessingResult.of(
                        ExternalSignalProcessingStatus.REJECTED,
                        signal.executionId(),
                        null,
                        null,
                        null,
                        validationErrors.getFirst()));
              }

              inboxStore.updateStates(
                  signal.sourceRef(),
                  signal.messageId(),
                  InboxValidationState.VALIDATED,
                  InboxProcessingState.PROCESSING,
                  null,
                  null);

              return resumeService
                  .applySignalAndResume(signal, wait)
                  .map(
                      outcome -> {
                        InboxProcessingState finalState =
                            outcome.status() == ExternalSignalProcessingStatus.ACCEPTED_AND_RESUMED
                                    || outcome.status()
                                        == ExternalSignalProcessingStatus.ACCEPTED_AND_TERMINATED
                                ? InboxProcessingState.PROCESSED
                                : InboxProcessingState.FAILED;
                        inboxStore.updateStates(
                            signal.sourceRef(),
                            signal.messageId(),
                            InboxValidationState.VALIDATED,
                            finalState,
                            null,
                            outcome.error() != null ? outcome.error().code() : null);

                        StepState stepState =
                            stepStore
                                .find(signal.executionId(), signal.stepId())
                                .map(s -> s.state())
                                .orElse(null);

                        return ExternalSignalProcessingResult.of(
                            outcome.status(),
                            signal.executionId(),
                            outcome.result() != null ? outcome.result().state() : ExecutionState.WAITING_EXTERNAL,
                            stepState,
                            outcome.result(),
                            outcome.error());
                      });
            });
  }

  private static CanonicalError error(String code, String message) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(ErrorCategory.VALIDATION)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("external_signal_app", null, null, null))
        .build();
  }
}
