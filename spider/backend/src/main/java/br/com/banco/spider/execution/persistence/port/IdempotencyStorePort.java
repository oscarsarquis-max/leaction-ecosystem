package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState;
import br.com.banco.spider.execution.persistence.model.IdempotencyRecord;
import java.util.Optional;

public interface IdempotencyStorePort {
  void insert(IdempotencyRecord record);

  Optional<IdempotencyRecord> findByScopeAndKeyHash(String scopeHash, String idempotencyKeyHash);

  IdempotencyRecord update(
      String idempotencyRecordId,
      long expectedVersion,
      IdempotencyRecordState newState,
      String resultRef,
      java.time.Instant updatedAt);
}
