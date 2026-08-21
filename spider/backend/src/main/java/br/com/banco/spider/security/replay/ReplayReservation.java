package br.com.banco.spider.security.replay;

import java.time.Instant;
import java.util.Objects;

public record ReplayReservation(
    String reservationId,
    String replayScopeHash,
    String nonceHash,
    String messageFingerprint,
    String fingerprintVersion,
    String keyRef,
    String keyVersion,
    String integrityProfileRef,
    Instant firstSeenAt,
    Instant expiresAt,
    ReplayDecisionStatus status,
    long version) {

  public ReplayReservation {
    Objects.requireNonNull(reservationId, "reservationId");
    Objects.requireNonNull(replayScopeHash, "replayScopeHash");
    Objects.requireNonNull(nonceHash, "nonceHash");
    Objects.requireNonNull(messageFingerprint, "messageFingerprint");
    Objects.requireNonNull(firstSeenAt, "firstSeenAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
    Objects.requireNonNull(status, "status");
  }
}
