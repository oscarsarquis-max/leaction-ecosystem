package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import br.com.banco.spider.execution.callback.CallbackDeliveryAttempt;
import br.com.banco.spider.execution.callback.CallbackDeliveryAttemptState;
import br.com.banco.spider.execution.callback.CallbackDeliveryCertainty;
import br.com.banco.spider.execution.persistence.port.CallbackDeliveryAttemptStorePort;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryCallbackDeliveryAttemptStore implements CallbackDeliveryAttemptStorePort {

  private final Map<String, CallbackDeliveryAttempt> byId = new ConcurrentHashMap<>();
  private final Map<String, List<String>> byOutbox = new ConcurrentHashMap<>();

  @Override
  public synchronized void insert(CallbackDeliveryAttempt attempt) {
    if (byId.putIfAbsent(attempt.deliveryId(), attempt) != null) {
      throw new IllegalStateException("Attempt exists");
    }
    byOutbox
        .computeIfAbsent(attempt.outboxId(), k -> new ArrayList<>())
        .add(attempt.deliveryId());
  }

  @Override
  public Optional<CallbackDeliveryAttempt> findActive(String outboxId) {
    return findByOutboxId(outboxId).stream()
        .filter(a -> a.state() == CallbackDeliveryAttemptState.RUNNING)
        .findFirst();
  }

  @Override
  public List<CallbackDeliveryAttempt> findByOutboxId(String outboxId) {
    List<String> ids = byOutbox.getOrDefault(outboxId, List.of());
    List<CallbackDeliveryAttempt> list = new ArrayList<>();
    for (String id : ids) {
      CallbackDeliveryAttempt a = byId.get(id);
      if (a != null) {
        list.add(a);
      }
    }
    return List.copyOf(list);
  }

  @Override
  public synchronized CallbackDeliveryAttempt complete(
      String deliveryId,
      CallbackDeliveryAttemptState state,
      CallbackDeliveryCertainty certainty,
      Instant completedAt,
      ErrorCategory errorCategory,
      String errorCode,
      Boolean retryable,
      List<EvidenceReference> evidenceRefs) {
    CallbackDeliveryAttempt current = byId.get(deliveryId);
    if (current == null) {
      throw new IllegalStateException("Attempt not found");
    }
    if (current.state() != CallbackDeliveryAttemptState.RUNNING) {
      return current;
    }
    CallbackDeliveryAttempt updated =
        new CallbackDeliveryAttempt(
            current.deliveryId(),
            current.outboxId(),
            current.logicalCallbackId(),
            current.attemptNumber(),
            current.bindingRef(),
            current.startedAt(),
            current.deadline(),
            completedAt,
            state,
            certainty,
            errorCategory,
            errorCode,
            retryable,
            evidenceRefs);
    byId.put(deliveryId, updated);
    return updated;
  }

  public void clear() {
    byId.clear();
    byOutbox.clear();
  }
}
