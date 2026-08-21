package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import br.com.banco.spider.execution.callback.CallbackDeliveryAttempt;
import br.com.banco.spider.execution.callback.CallbackDeliveryAttemptState;
import br.com.banco.spider.execution.callback.CallbackDeliveryCertainty;
import br.com.banco.spider.execution.persistence.port.CallbackDeliveryAttemptStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.CallbackDeliveryAttemptEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.CallbackDeliveryAttemptJpaRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaCallbackDeliveryAttemptStoreAdapter implements CallbackDeliveryAttemptStorePort {

  private final CallbackDeliveryAttemptJpaRepository repo;

  public JpaCallbackDeliveryAttemptStoreAdapter(CallbackDeliveryAttemptJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public void insert(CallbackDeliveryAttempt attempt) {
    CallbackDeliveryAttemptEntity e = new CallbackDeliveryAttemptEntity();
    e.setDeliveryId(attempt.deliveryId());
    e.setOutboxId(attempt.outboxId());
    e.setLogicalCallbackId(attempt.logicalCallbackId());
    e.setAttemptNumber(attempt.attemptNumber());
    e.setBindingRef(attempt.bindingRef());
    e.setStartedAt(attempt.startedAt());
    e.setDeadline(attempt.deadline());
    e.setCompletedAt(attempt.completedAt());
    e.setState(attempt.state());
    e.setCertainty(attempt.certainty());
    e.setErrorCategory(attempt.errorCategory());
    e.setErrorCode(attempt.errorCode());
    e.setRetryable(attempt.retryable());
    repo.save(e);
  }

  @Override
  public Optional<CallbackDeliveryAttempt> findActive(String outboxId) {
    return repo.findByOutboxIdAndState(outboxId, CallbackDeliveryAttemptState.RUNNING)
        .map(this::toModel);
  }

  @Override
  public List<CallbackDeliveryAttempt> findByOutboxId(String outboxId) {
    return repo.findByOutboxIdOrderByAttemptNumberAsc(outboxId).stream().map(this::toModel).toList();
  }

  @Override
  @Transactional
  public CallbackDeliveryAttempt complete(
      String deliveryId,
      CallbackDeliveryAttemptState state,
      CallbackDeliveryCertainty certainty,
      Instant completedAt,
      ErrorCategory errorCategory,
      String errorCode,
      Boolean retryable,
      List<EvidenceReference> evidenceRefs) {
    CallbackDeliveryAttemptEntity e =
        repo.findById(deliveryId).orElseThrow(() -> new IllegalStateException("Attempt not found"));
    if (e.getState() != CallbackDeliveryAttemptState.RUNNING) {
      return toModel(e);
    }
    e.setState(state);
    e.setCertainty(certainty);
    e.setCompletedAt(completedAt);
    e.setErrorCategory(errorCategory);
    e.setErrorCode(errorCode);
    e.setRetryable(retryable);
    return toModel(repo.save(e));
  }

  private CallbackDeliveryAttempt toModel(CallbackDeliveryAttemptEntity e) {
    return new CallbackDeliveryAttempt(
        e.getDeliveryId(),
        e.getOutboxId(),
        e.getLogicalCallbackId(),
        e.getAttemptNumber(),
        e.getBindingRef(),
        e.getStartedAt(),
        e.getDeadline(),
        e.getCompletedAt(),
        e.getState(),
        e.getCertainty(),
        e.getErrorCategory(),
        e.getErrorCode(),
        e.getRetryable(),
        List.of());
  }
}
