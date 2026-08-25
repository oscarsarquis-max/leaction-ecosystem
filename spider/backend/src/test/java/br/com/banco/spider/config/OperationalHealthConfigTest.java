package br.com.banco.spider.config;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;

class OperationalHealthConfigTest {

  @Test
  void enabledHealthRequiresTelemetry() {
    OperationalHealthProperties health = new OperationalHealthProperties();
    health.setEnabled(true);
    OperationalTelemetryProperties telemetry = new OperationalTelemetryProperties();

    assertThrows(
        IllegalStateException.class, () -> OperationalHealthConfig.validate(health, telemetry));
  }

  @Test
  void defaultWindowMustBeAllowedAndSamplePositive() {
    OperationalHealthProperties health = new OperationalHealthProperties();
    health.setDefaultWindow(Duration.ofHours(12));
    health.setAllowedWindows(List.of(Duration.ofHours(24)));

    assertThrows(
        IllegalStateException.class,
        () -> OperationalHealthConfig.validate(health, new OperationalTelemetryProperties()));
  }

  @Test
  void validDefaultsPass() {
    assertDoesNotThrow(
        () ->
            OperationalHealthConfig.validate(
                new OperationalHealthProperties(), new OperationalTelemetryProperties()));
  }
}
