package br.com.banco.spider.execution.support;

import java.time.Clock;
import java.time.Instant;

public interface SpiderClock {
  Instant now();

  static SpiderClock systemUtc() {
    return () -> Instant.now(Clock.systemUTC());
  }

  static SpiderClock fixed(Instant instant) {
    return () -> instant;
  }
}
