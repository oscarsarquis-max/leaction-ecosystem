package br.com.segsense.application.consent;

import java.time.Duration;

public record ContextInstanceTtlSettings(Duration ttl) {

  public ContextInstanceTtlSettings {
    if (ttl == null || ttl.isZero() || ttl.isNegative() || ttl.compareTo(Duration.ofDays(30)) > 0) {
      throw new IllegalArgumentException("ttl");
    }
  }
}
