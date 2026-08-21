package br.com.banco.spider.execution.retry;

import java.time.Duration;
import org.springframework.stereotype.Component;

/** Backoff exponencial limitado e determinístico. Sem jitter neste incremento. */
@Component
public class ExponentialCappedBackoff implements BackoffStrategyPort {
  @Override
  public Duration nextBackoff(RetryPolicyDefinition policy, int completedAttempts) {
    return policy.backoffForAttempt(completedAttempts);
  }
}
