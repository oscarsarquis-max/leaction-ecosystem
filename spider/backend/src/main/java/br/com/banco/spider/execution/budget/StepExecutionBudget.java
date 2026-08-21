package br.com.banco.spider.execution.budget;

import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.Objects;

public record StepExecutionBudget(Instant stepDeadline, Duration remainingAtStart) {
  public StepExecutionBudget {
    Objects.requireNonNull(stepDeadline, "stepDeadline");
    Objects.requireNonNull(remainingAtStart, "remainingAtStart");
  }

  public boolean hasUsefulBudget(SpiderClock clock, Duration minimumUseful) {
    Duration rem = Duration.between(clock.now(), stepDeadline);
    return rem.compareTo(minimumUseful) > 0;
  }

  public Duration remaining(SpiderClock clock) {
    Duration d = Duration.between(clock.now(), stepDeadline);
    return d.isNegative() ? Duration.ZERO : d;
  }
}
