package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState;
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
@Table(name = "tb_protected_signal_envelope")
@Getter
@Setter
@NoArgsConstructor
public class ProtectedSignalEnvelopeEntity {

  @Id
  @Column(name = "protected_envelope_id", length = 120)
  private String protectedEnvelopeId;

  @Column(name = "inbox_logical_key", length = 200, nullable = false, unique = true)
  private String inboxLogicalKey;

  @Column(name = "data_protection_profile_ref", length = 200, nullable = false)
  private String dataProtectionProfileRef;

  @Column(name = "algorithm", length = 40, nullable = false)
  private String algorithm;

  @Column(name = "key_ref", length = 200, nullable = false)
  private String keyRef;

  @Column(name = "key_version", length = 40, nullable = false)
  private String keyVersion;

  @Column(name = "aad_version", length = 20, nullable = false)
  private String aadVersion;

  @Column(name = "iv_b64", length = 64, nullable = false)
  private String ivB64;

  @Column(name = "ciphertext_and_tag_b64", nullable = false, columnDefinition = "TEXT")
  private String ciphertextAndTagB64;

  @Column(name = "plaintext_digest", length = 128)
  private String plaintextDigest;

  @Column(name = "ciphertext_digest", length = 128)
  private String ciphertextDigest;

  @Column(name = "plaintext_size", nullable = false)
  private int plaintextSize;

  @Enumerated(EnumType.STRING)
  @Column(name = "state", length = 40, nullable = false)
  private ProtectedEnvelopeState state;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "consumed_at")
  private Instant consumedAt;

  @Column(name = "eligible_for_deletion_at")
  private Instant eligibleForDeletionAt;

  @Column(name = "lease_owner", length = 120)
  private String leaseOwner;

  @Column(name = "lease_until")
  private Instant leaseUntil;

  @Column(name = "optimistic_version", nullable = false)
  private long optimisticVersion;
}
