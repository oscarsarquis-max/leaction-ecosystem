package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.callback.CallbackDeliveryAttempt;
import br.com.banco.spider.execution.callback.CallbackDeliveryAttemptState;
import br.com.banco.spider.execution.callback.CallbackDeliveryCertainty;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface CallbackDeliveryAttemptStorePort {
  void insert(CallbackDeliveryAttempt attempt);

  Optional<CallbackDeliveryAttempt> findActive(String outboxId);

  List<CallbackDeliveryAttempt> findByOutboxId(String outboxId);

  CallbackDeliveryAttempt complete(
      String deliveryId,
      CallbackDeliveryAttemptState state,
      CallbackDeliveryCertainty certainty,
      Instant completedAt,
      ErrorCategory errorCategory,
      String errorCode,
      Boolean retryable,
      List<EvidenceReference> evidenceRefs);
}
