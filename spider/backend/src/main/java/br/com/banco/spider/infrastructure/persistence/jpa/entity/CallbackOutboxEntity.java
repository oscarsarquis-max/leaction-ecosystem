package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.callback.CallbackOutboxState;
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
@Table(name = "tb_callback_outbox")
@Getter
@Setter
@NoArgsConstructor
public class CallbackOutboxEntity {

  @Id
  @Column(name = "outbox_id", length = 120)
  private String outboxId;

  @Column(name = "logical_callback_id", nullable = false, unique = true, length = 160)
  private String logicalCallbackId;

  @Column(name = "execution_id", nullable = false, unique = true, length = 120)
  private String executionId;

  @Column(name = "callback_definition_ref", nullable = false, length = 200)
  private String callbackDefinitionRef;

  @Column(name = "binding_ref", nullable = false, length = 200)
  private String bindingRef;

  @Column(name = "contract_ref", nullable = false, length = 200)
  private String contractRef;

  @Column(name = "security_profile_ref", nullable = false, length = 200)
  private String securityProfileRef;

  @Column(name = "projection_ref", nullable = false, length = 120)
  private String projectionRef;

  @Column(name = "result_ref", nullable = false, length = 120)
  private String resultRef;

  @Column(name = "logical_idempotency_key_hash", nullable = false, length = 128)
  private String logicalIdempotencyKeyHash;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private CallbackOutboxState state;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "next_attempt_at", nullable = false)
  private Instant nextAttemptAt;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;

  @Column(name = "attempt_count", nullable = false)
  private int attemptCount;

  @Column(name = "state_version", nullable = false)
  private long stateVersion;

  @Column(name = "last_error_code", length = 80)
  private String lastErrorCode;
}
