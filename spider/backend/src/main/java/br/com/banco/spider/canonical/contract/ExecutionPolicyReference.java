package br.com.banco.spider.canonical.contract;

import java.time.Duration;

/**
 * Referências a políticas publicadas — proibido policy inline arbitrária.
 *
 * @param timeout limite solicitado (ISO-8601 duration na serialização)
 * @param retryPolicyRef referência versionada
 * @param resiliencePolicyRef referência versionada
 */
public record ExecutionPolicyReference(
    Duration timeout, String retryPolicyRef, String resiliencePolicyRef) {

  public ExecutionPolicyReference {
    if (timeout != null && (timeout.isNegative() || timeout.isZero())) {
      throw new IllegalArgumentException("timeout must be positive when present");
    }
    retryPolicyRef = blankToNull(retryPolicyRef);
    resiliencePolicyRef = blankToNull(resiliencePolicyRef);
  }

  private static String blankToNull(String v) {
    if (v == null) {
      return null;
    }
    String t = v.trim();
    return t.isEmpty() ? null : t;
  }

  public static ExecutionPolicyReference empty() {
    return new ExecutionPolicyReference(null, null, null);
  }
}
