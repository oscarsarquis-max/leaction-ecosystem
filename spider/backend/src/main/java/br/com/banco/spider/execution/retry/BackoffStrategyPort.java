package br.com.banco.spider.execution.retry;

import java.time.Duration;

public interface BackoffStrategyPort {
  Duration nextBackoff(RetryPolicyDefinition policy, int completedAttempts);
}
