package br.com.banco.spider.execution.fingerprint;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;

public interface CanonicalRequestFingerprintPort {
  /** Digests versionados; nunca inclui executionId/timestamp/trace. */
  FingerprintResult fingerprint(CanonicalExecutionRequest request);

  record FingerprintResult(String digest, String version) {}
}
