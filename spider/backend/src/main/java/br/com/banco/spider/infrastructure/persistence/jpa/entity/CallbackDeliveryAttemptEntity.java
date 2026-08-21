package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.execution.callback.CallbackDeliveryAttemptState;
import br.com.banco.spider.execution.callback.CallbackDeliveryCertainty;
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
@Table(name = "tb_callback_delivery_attempt")
@Getter
@Setter
@NoArgsConstructor
public class CallbackDeliveryAttemptEntity {

  @Id
  @Column(name = "delivery_id", length = 120)
  private String deliveryId;

  @Column(name = "outbox_id", nullable = false, length = 120)
  private String outboxId;

  @Column(name = "logical_callback_id", nullable = false, length = 160)
  private String logicalCallbackId;

  @Column(name = "attempt_number", nullable = false)
  private int attemptNumber;

  @Column(name = "binding_ref", nullable = false, length = 200)
  private String bindingRef;

  @Column(name = "started_at", nullable = false)
  private Instant startedAt;

  @Column(nullable = false)
  private Instant deadline;

  @Column(name = "completed_at")
  private Instant completedAt;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private CallbackDeliveryAttemptState state;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private CallbackDeliveryCertainty certainty;

  @Enumerated(EnumType.STRING)
  @Column(name = "error_category", length = 40)
  private ErrorCategory errorCategory;

  @Column(name = "error_code", length = 80)
  private String errorCode;

  private Boolean retryable;
}
