package br.com.banco.spider.security.dataprotection;

import java.util.Objects;

public record DataProtectionKeyReference(
    String keyRef, String keyVersion, DataProtectionPurpose purpose, DataProtectionAlgorithm algorithm) {

  public DataProtectionKeyReference {
    Objects.requireNonNull(keyRef, "keyRef");
    Objects.requireNonNull(keyVersion, "keyVersion");
    Objects.requireNonNull(purpose, "purpose");
    Objects.requireNonNull(algorithm, "algorithm");
  }
}
