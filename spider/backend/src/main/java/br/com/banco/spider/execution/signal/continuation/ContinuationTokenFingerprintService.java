package br.com.banco.spider.execution.signal.continuation;

import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import br.com.banco.spider.security.integrity.FingerprintAlgorithmVersion;
import br.com.banco.spider.security.integrity.SensitiveFingerprintService;
import br.com.banco.spider.security.integrity.VersionedFingerprint;
import java.nio.charset.StandardCharsets;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class ContinuationTokenFingerprintService {

  public static final String DOMAIN = "SPIDER_CONTINUATION_TOKEN_V1";

  private final SensitiveFingerprintService fingerprints;

  public ContinuationTokenFingerprintService(
      SensitiveFingerprintService fingerprints, Sha256IdempotencyKeyHash sha256) {
    this.fingerprints = fingerprints;
  }

  public Mono<ContinuationTokenFingerprint> fingerprint(ContinuationToken token) {
    return fingerprints
        .fingerprint(DOMAIN, token.wire(), null)
        .map(this::toContinuationFp)
        .onErrorResume(ex -> Mono.just(legacySha(token)));
  }

  public ContinuationTokenFingerprint legacySha(ContinuationToken token) {
    VersionedFingerprint v1 = fingerprints.fingerprintV1(DOMAIN + "|" + token.wire());
    return new ContinuationTokenFingerprint(
        FingerprintAlgorithmVersion.V1_SHA256, null, null, v1.digest());
  }

  public boolean matchesConstantTime(ContinuationTokenFingerprint a, ContinuationTokenFingerprint b) {
    if (a == null || b == null) {
      return false;
    }
    if (a.algorithmVersion() != b.algorithmVersion()) {
      return false;
    }
    byte[] left = a.digest().getBytes(StandardCharsets.UTF_8);
    byte[] right = b.digest().getBytes(StandardCharsets.UTF_8);
    if (left.length != right.length) {
      return false;
    }
    int r = 0;
    for (int i = 0; i < left.length; i++) {
      r |= left[i] ^ right[i];
    }
    return r == 0;
  }

  private ContinuationTokenFingerprint toContinuationFp(VersionedFingerprint vf) {
    return new ContinuationTokenFingerprint(
        vf.algorithmVersion(), vf.keyRef(), vf.keyVersion(), vf.digest());
  }
}
