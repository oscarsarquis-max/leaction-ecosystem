package br.com.banco.spider.canonical.contract;

import java.time.Instant;
import java.util.Objects;

/** Identidade imutável da execução. */
public record ExecutionIdentity(String executionId, Instant timestamp, String idempotencyKey) {

  public ExecutionIdentity {
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(timestamp, "timestamp");
    executionId = executionId.trim();
    if (executionId.isEmpty()) {
      throw new IllegalArgumentException("executionId must not be blank");
    }
    if (idempotencyKey != null) {
      idempotencyKey = idempotencyKey.trim();
      if (idempotencyKey.isEmpty()) {
        idempotencyKey = null;
      }
    }
  }
}
