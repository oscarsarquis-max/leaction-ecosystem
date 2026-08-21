package br.com.banco.spider.application.canonical;

import br.com.banco.spider.canonical.contract.CallbackDeliverySummary;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.canonical.versioning.VersionedReference;
import br.com.banco.spider.execution.callback.CallbackOutboxRecord;
import br.com.banco.spider.execution.callback.CallbackReconciliationRecord;
import br.com.banco.spider.execution.callback.CallbackReconciliationState;
import br.com.banco.spider.execution.persistence.ReactiveExecutionPersistenceGateway;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.infrastructure.persistence.BlockingPersistenceSupport;
import java.time.Instant;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class GetCanonicalExecutionUseCase {

  private static final Logger log = LoggerFactory.getLogger(GetCanonicalExecutionUseCase.class);

  private final ReactiveExecutionPersistenceGateway persistence;
  private final CallbackOutboxStorePort outboxStore;
  private final CallbackReconciliationStorePort reconciliationStore;
  private final BlockingPersistenceSupport blocking;

  @Autowired
  public GetCanonicalExecutionUseCase(
      ReactiveExecutionPersistenceGateway persistence,
      CallbackOutboxStorePort outboxStore,
      @Autowired(required = false) CallbackReconciliationStorePort reconciliationStore,
      BlockingPersistenceSupport blocking) {
    this.persistence = persistence;
    this.outboxStore = outboxStore;
    this.reconciliationStore = reconciliationStore;
    this.blocking = blocking;
  }

  public record GetCanonicalExecutionQuery(
      String executionId, String authenticatedPrincipalRef, String requestedContractVersion) {}

  public record GetOutcome(
      boolean authorized,
      boolean found,
      ExecutionControlRecord control,
      CanonicalExecutionResult result,
      CallbackDeliverySummary callbackSummary,
      CanonicalError error) {}

  public Mono<GetOutcome> get(GetCanonicalExecutionQuery query) {
    return persistence
        .findControl(query.executionId())
        .flatMap(
            opt -> {
              if (opt.isEmpty()) {
                log.info("event=status_query_denied reasonCode=NOT_FOUND_OR_FOREIGN");
                return Mono.just(hidden());
              }
              ExecutionControlRecord control = opt.get();
              if (control.ownerPrincipalRef() == null
                  || !Objects.equals(
                      control.ownerPrincipalRef(), query.authenticatedPrincipalRef())) {
                log.info("event=status_query_denied reasonCode=OWNERSHIP");
                return Mono.just(hidden());
              }
              log.info("event=status_query_authorized executionId={}", query.executionId());
              return persistence
                  .findResultByExecutionId(control.executionId())
                  .flatMap(
                      resOpt -> {
                        Mono<CanonicalExecutionResult> resultMono =
                            resOpt.isEmpty()
                                ? Mono.just((CanonicalExecutionResult) null)
                                : persistence.loadResult(resOpt.get());
                        return resultMono.flatMap(
                            result ->
                                blocking
                                    .defer(() -> buildSummary(control.executionId()))
                                    .map(
                                        summary -> {
                                          log.info(
                                              "event=callback_summary_queried executionId={}",
                                              control.executionId());
                                          return new GetOutcome(
                                              true, true, control, result, summary.orElse(null), null);
                                        }));
                      });
            });
  }

  private Optional<CallbackDeliverySummary> buildSummary(String executionId) {
    Optional<CallbackOutboxRecord> outboxOpt = outboxStore.findByExecutionId(executionId);
    if (outboxOpt.isEmpty()) {
      return Optional.empty();
    }
    CallbackOutboxRecord outbox = outboxOpt.get();
    Optional<CallbackReconciliationRecord> rec =
        reconciliationStore == null
            ? Optional.empty()
            : reconciliationStore.findByExecutionId(executionId);
    return Optional.of(toSummary(outbox, rec.orElse(null)));
  }

  private CallbackDeliverySummary toSummary(
      CallbackOutboxRecord outbox, CallbackReconciliationRecord reconciliation) {
    String[] parts = outbox.callbackDefinitionRef().split("@", 2);
    VersionedReference ref =
        parts.length == 2
            ? VersionedReference.of(parts[0], parts[1])
            : VersionedReference.of(outbox.callbackDefinitionRef());
    String confirmation =
        reconciliation == null
            ? (outbox.state().name().equals("DELIVERED") ? "CONFIRMED" : "PENDING")
            : switch (reconciliation.state()) {
              case CONFIRMED_DELIVERED -> "CONFIRMED";
              case CONFIRMED_REJECTED, CONFIRMED_ABSENT -> "FAILED";
              case EXPIRED -> "EXPIRED";
              case MANUAL_REVIEW, UNKNOWN, EXHAUSTED -> "INCONCLUSIVE";
              default -> "RECONCILING";
            };
    Instant confirmedAt =
        reconciliation != null
                && reconciliation.state() == CallbackReconciliationState.CONFIRMED_DELIVERED
            ? reconciliation.updatedAt()
            : (outbox.state().name().equals("DELIVERED") ? outbox.nextAttemptAt() : null);
    boolean manual =
        reconciliation != null
            && (reconciliation.state() == CallbackReconciliationState.MANUAL_REVIEW
                || reconciliation.state() == CallbackReconciliationState.UNKNOWN);
    return new CallbackDeliverySummary(
        ref,
        outbox.state().name(),
        outbox.attemptCount(),
        outbox.nextAttemptAt(),
        outbox.lastErrorCode(),
        confirmation,
        reconciliation != null ? reconciliation.state().name() : null,
        outbox.attemptCount(),
        reconciliation != null ? reconciliation.queryCount() : 0,
        reconciliation != null && reconciliation.lastDisposition() != null
            ? reconciliation.lastDisposition().name()
            : null,
        reconciliation != null ? reconciliation.nextQueryAt() : outbox.nextAttemptAt(),
        confirmedAt,
        manual);
  }

  private static GetOutcome hidden() {
    return new GetOutcome(
        false,
        false,
        null,
        null,
        null,
        error("EXECUTION_NOT_VISIBLE", "Execution not visible", ErrorCategory.AUTHORIZATION));
  }

  private static CanonicalError error(String code, String message, ErrorCategory category) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(category)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("get_canonical", null, null, null))
        .build();
  }
}
