package br.com.banco.spider.execution.budget;

import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.Objects;

public record ExecutionDeadline(Instant absoluteDeadline) {
  public ExecutionDeadline {
    Objects.requireNonNull(absoluteDeadline, "absoluteDeadline");
  }

  public boolean isExpired(SpiderClock clock) {
    return !clock.now().isBefore(absoluteDeadline);
  }

  public Duration remaining(SpiderClock clock) {
    Duration d = Duration.between(clock.now(), absoluteDeadline);
    return d.isNegative() ? Duration.ZERO : d;
  }

  public static ExecutionDeadline fromNow(SpiderClock clock, Duration budget) {
    Objects.requireNonNull(budget, "budget");
    if (budget.isNegative() || budget.isZero()) {
      throw new IllegalArgumentException("budget must be positive");
    }
    return new ExecutionDeadline(clock.now().plus(budget));
  }
}
