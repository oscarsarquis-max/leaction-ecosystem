package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState;
import br.com.banco.spider.execution.persistence.model.IdempotencyRecord;
import br.com.banco.spider.execution.persistence.port.IdempotencyStorePort;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryIdempotencyStore implements IdempotencyStorePort {

  private final Map<String, IdempotencyRecord> byId = new ConcurrentHashMap<>();
  private final Map<String, String> scopeKeyToId = new ConcurrentHashMap<>();

  private static String key(String scopeHash, String keyHash) {
    return scopeHash + "|" + keyHash;
  }

  @Override
  public void insert(IdempotencyRecord record) {
    String sk = key(record.scopeHash(), record.idempotencyKeyHash());
    if (scopeKeyToId.putIfAbsent(sk, record.idempotencyRecordId()) != null) {
      throw new DuplicateIdempotencyException("Duplicate scope/key");
    }
    byId.put(record.idempotencyRecordId(), record);
  }

  @Override
  public Optional<IdempotencyRecord> findByScopeAndKeyHash(String scopeHash, String idempotencyKeyHash) {
    String id = scopeKeyToId.get(key(scopeHash, idempotencyKeyHash));
    return id == null ? Optional.empty() : Optional.ofNullable(byId.get(id));
  }

  @Override
  public IdempotencyRecord update(
      String idempotencyRecordId,
      long expectedVersion,
      IdempotencyRecordState newState,
      String resultRef,
      Instant updatedAt) {
    IdempotencyRecord current = byId.get(idempotencyRecordId);
    if (current == null) {
      throw new IllegalStateException("Idempotency record not found");
    }
    if (current.recordVersion() != expectedVersion) {
      throw new IllegalStateException("Idempotency version mismatch");
    }
    IdempotencyRecord updated =
        new IdempotencyRecord(
            current.idempotencyRecordId(),
            current.scopeHash(),
            current.idempotencyKeyHash(),
            current.requestFingerprint(),
            current.fingerprintVersion(),
            current.executionId(),
            newState,
            resultRef != null ? resultRef : current.resultRef(),
            current.createdAt(),
            updatedAt,
            current.expiresAt(),
            current.recordVersion() + 1);
    byId.put(idempotencyRecordId, updated);
    return updated;
  }

  public void clear() {
    byId.clear();
    scopeKeyToId.clear();
  }

  public static final class DuplicateIdempotencyException extends RuntimeException {
    public DuplicateIdempotencyException(String message) {
      super(message);
    }
  }
}
