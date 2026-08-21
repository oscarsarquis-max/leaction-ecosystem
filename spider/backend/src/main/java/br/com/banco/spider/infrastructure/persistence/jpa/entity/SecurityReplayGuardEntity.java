package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_security_replay_guard")
@Getter
@Setter
@NoArgsConstructor
public class SecurityReplayGuardEntity {

  @Id
  @Column(name = "reservation_id", length = 120)
  private String reservationId;

  @Column(name = "replay_scope_hash", nullable = false, length = 128)
  private String replayScopeHash;

  @Column(name = "nonce_hash", nullable = false, length = 128)
  private String nonceHash;

  @Column(name = "message_fingerprint", nullable = false, length = 200)
  private String messageFingerprint;

  @Column(name = "fingerprint_version", nullable = false, length = 40)
  private String fingerprintVersion;

  @Column(name = "key_ref", length = 200)
  private String keyRef;

  @Column(name = "key_version", length = 40)
  private String keyVersion;

  @Column(name = "integrity_profile_ref", length = 200)
  private String integrityProfileRef;

  @Column(name = "first_seen_at", nullable = false)
  private Instant firstSeenAt;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;

  @Column(nullable = false, length = 40)
  private String status;

  @Version
  @Column(nullable = false)
  private long version;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;
}
