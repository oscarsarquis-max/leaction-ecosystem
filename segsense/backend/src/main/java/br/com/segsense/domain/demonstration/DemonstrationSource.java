package br.com.segsense.domain.demonstration;

import java.time.LocalDate;
import java.util.UUID;

public record DemonstrationSource(
    UUID id,
    String key,
    String url,
    LocalDate consultedOn,
    String accessKind,
    String verificationStatus,
    String summary) {

  public boolean usableForClaim() {
    return "VERIFIED".equals(verificationStatus) || "VERIFIED_LIMITED".equals(verificationStatus);
  }
}
