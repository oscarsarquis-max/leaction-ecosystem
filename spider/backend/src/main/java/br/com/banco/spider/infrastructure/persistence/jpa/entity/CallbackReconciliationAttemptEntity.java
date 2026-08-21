package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.callback.CallbackDeliveryStatusDisposition;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_callback_reconciliation_attempt")
@Getter
@Setter
@NoArgsConstructor
public class CallbackReconciliationAttemptEntity {

  @Id
  @Column(name = "reconciliation_attempt_id", length = 120)
  private String reconciliationAttemptId;

  @Column(name = "reconciliation_id", nullable = false, length = 120)
  private String reconciliationId;

  @Column(name = "attempt_number", nullable = false)
  private int attemptNumber;

  @Column(name = "started_at", nullable = false)
  private Instant startedAt;

  @Column(name = "completed_at")
  private Instant completedAt;

  @Enumerated(EnumType.STRING)
  @Column(length = 60)
  private CallbackDeliveryStatusDisposition disposition;

  @Column(name = "safe_status_code", length = 40)
  private String safeStatusCode;

  @Column(name = "error_code", length = 80)
  private String errorCode;

  @Column(name = "error_category", length = 40)
  private String errorCategory;

  @Column(name = "next_query_at")
  private Instant nextQueryAt;

  @Column(name = "evidence_ref", length = 120)
  private String evidenceRef;

  @Column(name = "trace_correlation_id", length = 200)
  private String traceCorrelationId;
}
