package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.config.CapacityProperties;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.beans.factory.BeanCreationException;
import org.springframework.beans.factory.ObjectProvider;

final class CapacityTestSupport {

  static final Instant T0 = Instant.parse("2026-08-25T12:00:00Z");
  static final Duration WINDOW = Duration.ofMinutes(1);

  private CapacityTestSupport() {}

  static <T> ObjectProvider<T> provider(T value) {
    return new ObjectProvider<>() {
      @Override
      public T getObject() {
        if (value == null) {
          throw new BeanCreationException("no bean available in test provider");
        }
        return value;
      }

      @Override
      public T getObject(Object... args) {
        return getObject();
      }

      @Override
      public T getIfAvailable() {
        return value;
      }

      @Override
      public T getIfUnique() {
        return value;
      }
    };
  }

  static CapacityProperties properties(boolean enabled, boolean enforcing) {
    CapacityProperties properties = new CapacityProperties();
    properties.setEnabled(enabled);
    properties.getEnforcement().setEnabled(enforcing);
    return properties;
  }

  static CapacityTelemetry silentTelemetry() {
    return new CapacityTelemetry(
        provider((br.com.banco.spider.operational.events.OperationalEventPublisher) null));
  }

  static CapacityLimit limits(
      int maxConcurrency, int softBacklog, int hardBacklog, int quotaPerWindow) {
    return new CapacityLimit(
        maxConcurrency, softBacklog, hardBacklog, quotaPerWindow, WINDOW, Duration.ZERO);
  }

  static CapacityPolicy policy(String code, CapacityLimit limits) {
    return policy(code, limits, CapacityPolicyState.ACTIVE, 0, Duration.ZERO);
  }

  static CapacityPolicy policy(
      String code,
      CapacityLimit limits,
      CapacityPolicyState state,
      int circuitFailureThreshold,
      Duration circuitOpenDuration) {
    return new CapacityPolicy(
        "capacity:test:" + code,
        "1.0",
        CapacityScopeType.SCHEDULE,
        "sched:test-" + code + "@1",
        state,
        limits,
        circuitFailureThreshold,
        WINDOW,
        circuitOpenDuration,
        1,
        1,
        true);
  }

  static AdmissionRequest request(CapacityPolicy policy) {
    return request(policy, null);
  }

  static AdmissionRequest request(CapacityPolicy policy, String workerType) {
    return new AdmissionRequest(
        "test:" + policy.code(),
        CapacityScopeType.SCHEDULE,
        policy.scopeRef(),
        workerType,
        policy.scopeRef(),
        null,
        null,
        T0,
        "corr-test");
  }

  /** Relógio controlado pelo teste — nenhuma transição depende de tempo de parede. */
  static final class MutableClock implements SpiderClock {
    private final AtomicReference<Instant> current;

    MutableClock(Instant start) {
      this.current = new AtomicReference<>(start);
    }

    @Override
    public Instant now() {
      return current.get();
    }

    void advance(Duration amount) {
      current.updateAndGet(instant -> instant.plus(amount));
    }
  }
}
