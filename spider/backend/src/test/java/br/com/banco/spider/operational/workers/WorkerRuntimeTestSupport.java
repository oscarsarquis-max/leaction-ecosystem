package br.com.banco.spider.operational.workers;

import br.com.banco.spider.config.WorkerRuntimeProperties;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.beans.factory.BeanCreationException;
import org.springframework.beans.factory.ObjectProvider;

final class WorkerRuntimeTestSupport {

  private WorkerRuntimeTestSupport() {}

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

  static WorkerRuntimeTelemetry silentTelemetry() {
    return new WorkerRuntimeTelemetry(
        provider((br.com.banco.spider.operational.events.OperationalEventPublisher) null));
  }

  static WorkerRuntimeCatalog catalog() {
    return new WorkerRuntimeCatalog(
        10, Duration.ofSeconds(30), Duration.ofSeconds(20), 3);
  }

  static WorkerRuntimeProperties properties() {
    WorkerRuntimeProperties properties = new WorkerRuntimeProperties();
    properties.setEnabled(true);
    properties.setInstanceId("wrk-inst-test");
    properties.setHeartbeatInterval(Duration.ofSeconds(5));
    properties.setStaleAfter(Duration.ofSeconds(30));
    properties.setTickInterval(Duration.ofSeconds(10));
    properties.setDefaultBatchSize(10);
    properties.setDefaultLeaseDuration(Duration.ofSeconds(30));
    properties.setDefaultExecutionTimeout(Duration.ofSeconds(20));
    properties.setMaxConcurrency(2);
    properties.setDrainTimeout(Duration.ofSeconds(30));
    properties.setMaxAttempts(3);
    return properties;
  }

  /** Relógio controlado pelo teste — o runtime nunca depende de tempo de parede real. */
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
