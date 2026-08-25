package br.com.banco.spider.config;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

class FailureLabConfigTest {

  @Test
  void httpSurfaceRequiresFailureLabEnabled() {
    FailureLabProperties properties = new FailureLabProperties();
    properties.getHttp().setEnabled(true);

    IllegalStateException rejected =
        assertThrows(
            IllegalStateException.class, () -> FailureLabConfig.validate(properties, null));
    assertTrue(rejected.getMessage().contains("spider.failure-lab.http.enabled"));
  }

  @Test
  void localDemoRequiresFailureLabEnabled() {
    FailureLabProperties properties = new FailureLabProperties();
    properties.getLocalDemo().setEnabled(true);

    IllegalStateException rejected =
        assertThrows(
            IllegalStateException.class, () -> FailureLabConfig.validate(properties, null));
    assertTrue(rejected.getMessage().contains("spider.failure-lab.local-demo.enabled"));
  }

  @Test
  void concurrencyLimitMustBeAtLeastOne() {
    FailureLabProperties properties = new FailureLabProperties();
    properties.setMaxConcurrentRuns(0);

    assertThrows(IllegalStateException.class, () -> FailureLabConfig.validate(properties, null));
  }

  @Test
  void executionsPerRunMustStayWithinTheCatalogCeiling() {
    FailureLabProperties properties = new FailureLabProperties();
    properties.setMaxExecutionsPerRun(11);

    assertThrows(IllegalStateException.class, () -> FailureLabConfig.validate(properties, null));

    FailureLabProperties tooFew = new FailureLabProperties();
    tooFew.setMaxExecutionsPerRun(0);

    assertThrows(IllegalStateException.class, () -> FailureLabConfig.validate(tooFew, null));
  }

  @Test
  void runDurationIsCappedAtFifteenMinutes() {
    FailureLabProperties properties = new FailureLabProperties();
    properties.setMaxRunDuration(Duration.ofMinutes(20));

    assertThrows(IllegalStateException.class, () -> FailureLabConfig.validate(properties, null));

    FailureLabProperties zero = new FailureLabProperties();
    zero.setMaxRunDuration(Duration.ZERO);

    assertThrows(IllegalStateException.class, () -> FailureLabConfig.validate(zero, null));
  }

  @Test
  void disabledDefaultsAreValid() {
    assertDoesNotThrow(
        () -> FailureLabConfig.validate(new FailureLabProperties(), new MockEnvironment()));
  }

  @Test
  void enabledLabWithoutMockAdapterOnlyWarns() {
    FailureLabProperties properties = new FailureLabProperties();
    properties.setEnabled(true);
    properties.getHttp().setEnabled(true);
    MockEnvironment environment = new MockEnvironment();
    environment.setProperty("spider.adapter.mock.enabled", "false");

    assertDoesNotThrow(() -> FailureLabConfig.validate(properties, environment));
  }
}
