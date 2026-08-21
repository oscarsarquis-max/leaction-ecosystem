package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(
    name = "tb_idempotency_record",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_tb_idempotency_scope_key",
            columnNames = {"scope_hash", "idempotency_key_hash"}))
@Getter
@Setter
@NoArgsConstructor
public class IdempotencyRecordEntity {

  @Id
  @Column(name = "idempotency_record_id", length = 120)
  private String idempotencyRecordId;

  @Column(name = "scope_hash", nullable = false, length = 128)
  private String scopeHash;

  @Column(name = "idempotency_key_hash", nullable = false, length = 128)
  private String idempotencyKeyHash;

  @Column(name = "request_fingerprint", nullable = false, length = 128)
  private String requestFingerprint;

  @Column(name = "fingerprint_version", nullable = false, length = 20)
  private String fingerprintVersion;

  @Column(name = "execution_id", nullable = false, length = 120)
  private String executionId;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private IdempotencyRecordState state;

  @Column(name = "result_ref", length = 120)
  private String resultRef;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;

  @Column(name = "record_version", nullable = false)
  private long recordVersion;
}
