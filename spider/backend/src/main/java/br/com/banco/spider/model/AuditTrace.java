package br.com.banco.spider.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * Trace técnico da orquestração (audit).
 * Sem payload financeiro sensível como SoR.
 */
@Entity
@Table(name = "tb_audit_trace")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AuditTrace {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(name = "correlation_id", nullable = false)
  private UUID correlationId;

  @Column(name = "product_code", nullable = false, length = 100)
  private String productCode;

  @Column(name = "idempotency_key", length = 200)
  private String idempotencyKey;

  @Column(nullable = false, length = 40)
  private String status;

  @Column(name = "started_at", nullable = false)
  private Instant startedAt;

  @Column(name = "finished_at")
  private Instant finishedAt;

  @Column(name = "error_summary", length = 2000)
  private String errorSummary;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(nullable = false, columnDefinition = "jsonb")
  @Builder.Default
  private String metadata = "{}";

  @PrePersist
  void onCreate() {
    if (startedAt == null) {
      startedAt = Instant.now();
    }
    if (metadata == null) {
      metadata = "{}";
    }
    if (status == null) {
      status = "started";
    }
  }
}
