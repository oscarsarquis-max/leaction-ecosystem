package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxValidationState;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_inbox_message")
@IdClass(InboxMessageEntity.Pk.class)
@Getter
@Setter
@NoArgsConstructor
public class InboxMessageEntity {

  @Id
  @Column(name = "source_ref", length = 200)
  private String sourceRef;

  @Id
  @Column(name = "message_id", length = 120)
  private String messageId;

  @Column(name = "binding_ref", nullable = false, length = 200)
  private String bindingRef;

  @Column(name = "contract_ref", nullable = false, length = 200)
  private String contractRef;

  @Column(name = "deduplication_key_hash", nullable = false, length = 128)
  private String deduplicationKeyHash;

  @Column(name = "message_fingerprint", nullable = false, length = 128)
  private String messageFingerprint;

  @Column(name = "fingerprint_version", nullable = false, length = 20)
  private String fingerprintVersion;

  @Column(name = "execution_id", length = 120)
  private String executionId;

  @Column(name = "step_id", length = 120)
  private String stepId;

  @Column(name = "external_operation_ref", length = 200)
  private String externalOperationRef;

  @Column(name = "received_at", nullable = false)
  private Instant receivedAt;

  @Enumerated(EnumType.STRING)
  @Column(name = "validation_state", nullable = false, length = 40)
  private InboxValidationState validationState;

  @Enumerated(EnumType.STRING)
  @Column(name = "processing_state", nullable = false, length = 40)
  private InboxProcessingState processingState;

  @Column(name = "payload_ref", length = 120)
  private String payloadRef;

  @Column(name = "error_code", length = 80)
  private String errorCode;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;

  @Column(name = "wait_id", length = 120)
  private String waitId;

  @Column(name = "signal_definition_ref", length = 200)
  private String signalDefinitionRef;

  @Column(name = "payload_digest", length = 128)
  private String payloadDigest;

  @Column(name = "application_attempt_count")
  private Integer applicationAttemptCount;

  @Column(name = "next_attempt_at")
  private Instant nextAttemptAt;

  @Column(name = "lease_owner", length = 120)
  private String leaseOwner;

  @Column(name = "lease_until")
  private Instant leaseUntil;

  @Column(name = "optimistic_version")
  private Long optimisticVersion;

  @Column(name = "verified_at")
  private Instant verifiedAt;

  @Column(name = "applied_at")
  private Instant appliedAt;

  @Getter
  @Setter
  @NoArgsConstructor
  public static class Pk implements Serializable {
    private String sourceRef;
    private String messageId;

    public Pk(String sourceRef, String messageId) {
      this.sourceRef = sourceRef;
      this.messageId = messageId;
    }

    @Override
    public boolean equals(Object o) {
      if (this == o) return true;
      if (!(o instanceof Pk pk)) return false;
      return Objects.equals(sourceRef, pk.sourceRef) && Objects.equals(messageId, pk.messageId);
    }

    @Override
    public int hashCode() {
      return Objects.hash(sourceRef, messageId);
    }
  }
}
