package br.com.banco.spider.config;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.Duration;
import java.util.function.Consumer;
import org.junit.jupiter.api.Test;

class WorkerRuntimeConfigTest {

  @Test
  void defaultsAreDisabledAndValid() {
    WorkerRuntimeProperties properties = new WorkerRuntimeProperties();
    assertDoesNotThrow(() -> WorkerRuntimeConfig.validate(properties));
    org.junit.jupiter.api.Assertions.assertFalse(properties.isEnabled());
    org.junit.jupiter.api.Assertions.assertFalse(properties.getHttp().isEnabled());
    org.junit.jupiter.api.Assertions.assertFalse(properties.getLocalDemo().isEnabled());
    org.junit.jupiter.api.Assertions.assertFalse(properties.getRecovery().isEnabled());
    org.junit.jupiter.api.Assertions.assertFalse(properties.isAllowDrain());
  }

  @Test
  void httpSurfaceRequiresTheRuntimeItself() {
    assertRejected(properties -> properties.getHttp().setEnabled(true));
  }

  @Test
  void localDemoRequiresTheRuntimeItself() {
    assertRejected(properties -> properties.getLocalDemo().setEnabled(true));
  }

  @Test
  void heartbeatMustBeShorterThanStaleWindow() {
    assertRejected(
        properties -> {
          properties.setHeartbeatInterval(Duration.ofSeconds(30));
          properties.setStaleAfter(Duration.ofSeconds(20));
        });
  }

  @Test
  void leaseMustOutliveTheHeartbeat() {
    assertRejected(
        properties -> {
          properties.setHeartbeatInterval(Duration.ofSeconds(30));
          properties.setStaleAfter(Duration.ofSeconds(60));
          properties.setDefaultLeaseDuration(Duration.ofSeconds(30));
        });
  }

  @Test
  void tickMustBeShorterThanStaleWindow() {
    assertRejected(properties -> properties.setTickInterval(Duration.ofSeconds(25)));
  }

  @Test
  void tickIsCappedToAvoidASleepingRuntime() {
    assertRejected(
        properties -> {
          properties.setStaleAfter(Duration.ofMinutes(5));
          properties.setTickInterval(Duration.ofMinutes(2));
        });
  }

  @Test
  void batchSizeIsBounded() {
    assertRejected(properties -> properties.setDefaultBatchSize(0));
    assertRejected(properties -> properties.setDefaultBatchSize(101));
  }

  @Test
  void concurrencyIsBounded() {
    assertRejected(properties -> properties.setMaxConcurrency(0));
    assertRejected(properties -> properties.setMaxConcurrency(17));
  }

  @Test
  void attemptsAreBounded() {
    assertRejected(properties -> properties.setMaxAttempts(0));
    assertRejected(properties -> properties.setMaxAttempts(11));
  }

  @Test
  void executionTimeoutCannotExceedTheLease() {
    assertRejected(
        properties -> {
          properties.setDefaultLeaseDuration(Duration.ofSeconds(10));
          properties.setDefaultExecutionTimeout(Duration.ofSeconds(20));
        });
  }

  @Test
  void nonPositiveDurationsAreRejected() {
    assertRejected(properties -> properties.setHeartbeatInterval(Duration.ZERO));
    assertRejected(properties -> properties.setDrainTimeout(Duration.ofSeconds(-1)));
  }

  @Test
  void enabledRuntimeWithCoherentWindowsIsAccepted() {
    WorkerRuntimeProperties properties = new WorkerRuntimeProperties();
    properties.setEnabled(true);
    properties.getHttp().setEnabled(true);
    properties.getLocalDemo().setEnabled(true);
    properties.getRecovery().setEnabled(true);
    properties.setHeartbeatInterval(Duration.ofSeconds(2));
    properties.setStaleAfter(Duration.ofSeconds(10));
    properties.setTickInterval(Duration.ofMillis(500));
    properties.setDefaultLeaseDuration(Duration.ofSeconds(15));
    properties.setDefaultExecutionTimeout(Duration.ofSeconds(10));
    assertDoesNotThrow(() -> WorkerRuntimeConfig.validate(properties));
  }

  private static void assertRejected(Consumer<WorkerRuntimeProperties> mutation) {
    WorkerRuntimeProperties properties = new WorkerRuntimeProperties();
    mutation.accept(properties);
    assertThrows(IllegalStateException.class, () -> WorkerRuntimeConfig.validate(properties));
  }
}
