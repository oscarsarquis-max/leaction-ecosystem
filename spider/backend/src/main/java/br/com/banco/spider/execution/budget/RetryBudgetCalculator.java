package br.com.banco.spider.execution.budget;

import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;

public final class RetryBudgetCalculator {
  private RetryBudgetCalculator() {}

  public static StepExecutionBudget forStep(
      ExecutionDeadline executionDeadline, SpiderClock clock, Duration stepTimeoutCap) {
    Duration remaining = executionDeadline.remaining(clock);
    Duration effective =
        stepTimeoutCap == null || stepTimeoutCap.compareTo(remaining) > 0
            ? remaining
            : stepTimeoutCap;
    Instant stepDeadline = clock.now().plus(effective);
    if (stepDeadline.isAfter(executionDeadline.absoluteDeadline())) {
      stepDeadline = executionDeadline.absoluteDeadline();
    }
    return new StepExecutionBudget(stepDeadline, effective);
  }

  public static boolean canScheduleBackoff(
      ExecutionDeadline executionDeadline, SpiderClock clock, Duration backoff) {
    if (backoff == null || backoff.isNegative() || backoff.isZero()) {
      return !executionDeadline.isExpired(clock);
    }
    Instant after = clock.now().plus(backoff);
    return after.isBefore(executionDeadline.absoluteDeadline());
  }
}
