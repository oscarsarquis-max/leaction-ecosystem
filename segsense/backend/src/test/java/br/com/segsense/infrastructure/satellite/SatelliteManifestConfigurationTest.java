package br.com.segsense.infrastructure.satellite;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.segsense.application.satellite.SatelliteManifest;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.ClassPathResource;

class SatelliteManifestConfigurationTest {

  @Test
  void loadsValidClasspathManifest() throws Exception {
    SatelliteManifest manifest =
        SatelliteManifestConfiguration.load(
            new ClassPathResource("satellite-manifest.yaml"), "SEGSENSE");

    assertThat(manifest.classification()).isEqualTo("DRAFT / NOT_CERTIFIED");
    assertThat(manifest.schemaVersionKind()).isEqualTo("PRELIMINARY");
    assertThat(manifest.applicationId()).isEqualTo("SEGSENSE");
    assertThat(manifest.domain()).isEqualTo("INSURANCE");
    assertThat(manifest.allowedOperationClasses()).containsExactly("READ", "SIMULATE", "REQUEST");
    assertThat(manifest.mutationPolicy()).isEqualTo("CONFIRMATION_REQUIRED");
    assertThat(manifest.status()).isEqualTo("DRAFT");
    assertThat(manifest.executable()).isFalse();
    assertThat(manifest.acceptedBySpider()).isFalse();
  }

  @Test
  void failsWhenManifestApplicationIdDiverges() {
    ByteArrayResource resource =
        new ByteArrayResource(
            """
            classification: "DRAFT / NOT_CERTIFIED"
            schemaVersion: segsense-local-preliminary-1
            schemaVersionKind: PRELIMINARY
            applicationId: OTHER
            domain: INSURANCE
            allowedOperationClasses:
              - READ
            mutationPolicy: CONFIRMATION_REQUIRED
            status: DRAFT
            executable: false
            acceptedBySpider: false
            """
                .getBytes());

    assertThatThrownBy(() -> SatelliteManifestConfiguration.load(resource, "SEGSENSE"))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("does not match local configuration");
  }
}
