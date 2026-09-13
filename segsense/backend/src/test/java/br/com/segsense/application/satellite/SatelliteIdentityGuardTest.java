package br.com.segsense.application.satellite;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class SatelliteIdentityGuardTest {

  @Test
  void acceptsMatchingApplicationId() {
    assertThatCode(() -> SatelliteIdentityGuard.requireMatching("SEGSENSE", "SEGSENSE"))
        .doesNotThrowAnyException();
  }

  @Test
  void failsWhenApplicationIdDiverges() {
    assertThatThrownBy(() -> SatelliteIdentityGuard.requireMatching("SEGSENSE", "OTHER"))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("does not match local configuration");
  }

  @Test
  void failsWhenConfiguredApplicationIdIsMissing() {
    assertThatThrownBy(() -> SatelliteIdentityGuard.requireMatching(null, "SEGSENSE"))
        .isInstanceOf(IllegalStateException.class);
  }
}
