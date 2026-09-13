package br.com.segsense.application.link;

import java.time.Duration;
import java.time.Instant;

public record LinkTtlSettings(int maxTtlDays, int absoluteMaxTtlDays) {

  public LinkTtlSettings {
    if (maxTtlDays < 1 || absoluteMaxTtlDays < 1 || maxTtlDays > absoluteMaxTtlDays) {
      throw new IllegalArgumentException("ttl");
    }
    if (absoluteMaxTtlDays > 90) {
      throw new IllegalArgumentException("absoluteMaxTtlDays");
    }
  }

  public Instant latestAllowed(Instant now) {
    int days = Math.min(maxTtlDays, absoluteMaxTtlDays);
    return now.plus(Duration.ofDays(days));
  }
}
