package br.com.banco.spider.execution.signal.continuation;

import br.com.banco.spider.security.integrity.FingerprintAlgorithmVersion;
import java.util.Objects;

public record ContinuationTokenFingerprint(
    FingerprintAlgorithmVersion algorithmVersion,
    String keyRef,
    String keyVersion,
    String digest) {

  public ContinuationTokenFingerprint {
    Objects.requireNonNull(algorithmVersion, "algorithmVersion");
    Objects.requireNonNull(digest, "digest");
    digest = digest.trim();
    if (digest.isEmpty()) {
      throw new IllegalArgumentException("digest blank");
    }
  }

  public String wireForm() {
    if (algorithmVersion == FingerprintAlgorithmVersion.V1_SHA256) {
      return "v1:" + digest;
    }
    return "v2:" + (keyVersion == null ? "" : keyVersion) + ":" + digest;
  }
}
