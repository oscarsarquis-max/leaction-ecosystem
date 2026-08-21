package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.execution.wait.WaitType;
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
@Table(name = "tb_execution_wait")
@Getter
@Setter
@NoArgsConstructor
public class ExecutionWaitEntity {

  @Id
  @Column(name = "wait_id", length = 120)
  private String waitId;

  @Column(name = "execution_id", nullable = false, length = 120)
  private String executionId;

  @Column(name = "step_id", nullable = false, length = 120)
  private String stepId;

  @Column(name = "attempt_id", nullable = false, length = 120)
  private String attemptId;

  @Enumerated(EnumType.STRING)
  @Column(name = "wait_type", nullable = false, length = 60)
  private WaitType waitType;

  @Column(name = "wait_policy_ref", nullable = false, length = 200)
  private String waitPolicyRef;

  @Column(name = "external_operation_ref", length = 200)
  private String externalOperationRef;

  @Column(name = "expected_signal_contract_ref", length = 200)
  private String expectedSignalContractRef;

  @Column(name = "expected_source_ref", length = 200)
  private String expectedSourceRef;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private WaitState state;

  @Column(name = "state_version", nullable = false)
  private long stateVersion;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "earliest_resume_at")
  private Instant earliestResumeAt;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;

  @Column(name = "received_message_id", length = 120)
  private String receivedMessageId;

  @Column(name = "resolved_at")
  private Instant resolvedAt;

  @Column(name = "resolution_reason_code", length = 80)
  private String resolutionReasonCode;

  @Column(name = "signal_definition_ref", length = 200)
  private String signalDefinitionRef;

  @Column(name = "integrity_profile_ref", length = 200)
  private String integrityProfileRef;

  @Column(name = "continuation_token_fingerprint", length = 128)
  private String continuationTokenFingerprint;

  @Column(name = "continuation_token_fp_version", length = 40)
  private String continuationTokenFingerprintVersion;

  @Column(name = "continuation_token_key_ref", length = 200)
  private String continuationTokenKeyRef;

  @Column(name = "continuation_token_key_version", length = 40)
  private String continuationTokenKeyVersion;

  @Column(name = "continuation_token_expires_at")
  private Instant continuationTokenExpiresAt;

  @Column(name = "data_protection_profile_ref", length = 200)
  private String dataProtectionProfileRef;
}
