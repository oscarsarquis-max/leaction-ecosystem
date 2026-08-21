package br.com.banco.spider.security.integrity;

import java.util.Objects;

public record VersionedFingerprint(
    FingerprintAlgorithmVersion algorithmVersion,
    String keyRef,
    String keyVersion,
    String digest) {

  public VersionedFingerprint {
    Objects.requireNonNull(algorithmVersion, "algorithmVersion");
    Objects.requireNonNull(digest, "digest");
  }

  public String wireForm() {
    if (algorithmVersion == FingerprintAlgorithmVersion.V1_SHA256) {
      return "v1:" + digest;
    }
    return "v2:" + keyVersion + ":" + digest;
  }
}
