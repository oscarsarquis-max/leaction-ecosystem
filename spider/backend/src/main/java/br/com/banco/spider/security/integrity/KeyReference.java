package br.com.banco.spider.security.integrity;

import java.util.Objects;

public record KeyReference(
    String keyRef, String keyVersion, IntegrityPurpose purpose, IntegrityAlgorithm algorithm) {

  public KeyReference {
    Objects.requireNonNull(keyRef, "keyRef");
    Objects.requireNonNull(keyVersion, "keyVersion");
    Objects.requireNonNull(purpose, "purpose");
    Objects.requireNonNull(algorithm, "algorithm");
  }
}
