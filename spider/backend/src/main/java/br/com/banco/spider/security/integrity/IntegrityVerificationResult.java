package br.com.banco.spider.security.integrity;

import java.util.Objects;

public record IntegrityVerificationResult(IntegrityVerificationDisposition disposition) {
  public IntegrityVerificationResult {
    Objects.requireNonNull(disposition, "disposition");
  }

  public boolean verified() {
    return disposition == IntegrityVerificationDisposition.VERIFIED;
  }
}
