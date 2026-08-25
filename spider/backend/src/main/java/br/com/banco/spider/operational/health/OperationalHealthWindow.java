package br.com.banco.spider.operational.health;

import java.time.Duration;
import java.time.Instant;
import java.util.Objects;

public record OperationalHealthWindow(
    int schemaVersion, Instant from, Instant to, String duration) {
  public OperationalHealthWindow {
    if (schemaVersion != 1) {
      throw new IllegalArgumentException("Only schemaVersion 1 is supported");
    }
    Objects.requireNonNull(from, "from");
    Objects.requireNonNull(to, "to");
    Objects.requireNonNull(duration, "duration");
    if (to.isBefore(from)) {
      throw new IllegalArgumentException("to must not be before from");
    }
  }

  public static OperationalHealthWindow endingAt(Instant to, Duration duration) {
    return new OperationalHealthWindow(1, to.minus(duration), to, duration.toString());
  }
}
