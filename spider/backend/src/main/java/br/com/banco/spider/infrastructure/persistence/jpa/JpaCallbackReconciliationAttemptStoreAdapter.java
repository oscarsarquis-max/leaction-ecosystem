package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.callback.CallbackReconciliationAttempt;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationAttemptStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.CallbackReconciliationAttemptEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.CallbackReconciliationAttemptJpaRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaCallbackReconciliationAttemptStoreAdapter
    implements CallbackReconciliationAttemptStorePort {

  private final CallbackReconciliationAttemptJpaRepository repo;

  public JpaCallbackReconciliationAttemptStoreAdapter(
      CallbackReconciliationAttemptJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public void insert(CallbackReconciliationAttempt attempt) {
    CallbackReconciliationAttemptEntity e = new CallbackReconciliationAttemptEntity();
    e.setReconciliationAttemptId(attempt.reconciliationAttemptId());
    e.setReconciliationId(attempt.reconciliationId());
    e.setAttemptNumber(attempt.attemptNumber());
    e.setStartedAt(attempt.startedAt());
    e.setCompletedAt(attempt.completedAt());
    e.setDisposition(attempt.disposition());
    e.setSafeStatusCode(attempt.safeStatusCode());
    if (attempt.canonicalError() != null) {
      e.setErrorCode(attempt.canonicalError().code());
      e.setErrorCategory(
          attempt.canonicalError().category() != null
              ? attempt.canonicalError().category().name()
              : null);
    }
    e.setNextQueryAt(attempt.nextQueryAt());
    e.setEvidenceRef(attempt.evidenceRef());
    e.setTraceCorrelationId(attempt.traceCorrelationId());
    repo.save(e);
  }

  @Override
  public Optional<CallbackReconciliationAttempt> findByReconciliationAndNumber(
      String reconciliationId, int attemptNumber) {
    return repo.findByReconciliationIdAndAttemptNumber(reconciliationId, attemptNumber)
        .map(this::toModel);
  }

  @Override
  public List<CallbackReconciliationAttempt> findByReconciliationId(String reconciliationId) {
    return repo.findByReconciliationIdOrderByAttemptNumberAsc(reconciliationId).stream()
        .map(this::toModel)
        .toList();
  }

  @Override
  public int countByReconciliationId(String reconciliationId) {
    return repo.countByReconciliationId(reconciliationId);
  }

  private CallbackReconciliationAttempt toModel(CallbackReconciliationAttemptEntity e) {
    CanonicalError err = null;
    if (e.getErrorCode() != null) {
      ErrorCategory cat = ErrorCategory.INTERNAL;
      try {
        if (e.getErrorCategory() != null) {
          cat = ErrorCategory.valueOf(e.getErrorCategory());
        }
      } catch (IllegalArgumentException ignored) {
        // keep INTERNAL
      }
      err =
          CanonicalError.builder()
              .errorId("err-" + UUID.randomUUID())
              .code(e.getErrorCode())
              .category(cat)
              .severity(ErrorSeverity.ERROR)
              .message(e.getErrorCode())
              .retryable(false)
              .occurredAt(Instant.now())
              .source(new CanonicalError.ErrorSource("reconciliation_attempt", null, null, null))
              .build();
    }
    return new CallbackReconciliationAttempt(
        e.getReconciliationAttemptId(),
        e.getReconciliationId(),
        e.getAttemptNumber(),
        e.getStartedAt(),
        e.getCompletedAt(),
        e.getDisposition(),
        e.getSafeStatusCode(),
        err,
        e.getNextQueryAt(),
        e.getEvidenceRef(),
        e.getTraceCorrelationId());
  }
}
