package br.com.segsense.application.system;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import br.com.segsense.application.satellite.SatelliteSettings;
import br.com.segsense.domain.system.OperationalState;
import br.com.segsense.domain.system.SystemInfo;
import org.junit.jupiter.api.Test;

class SystemInfoServiceTest {

  @Test
  void reportsConfiguredIdentityAndOperationalState() {
    OperationalHealthPort healthPort = mock(OperationalHealthPort.class);
    SatelliteSettings settings = mock(SatelliteSettings.class);
    when(healthPort.currentState()).thenReturn(OperationalState.UP);
    when(settings.name()).thenReturn("SegSense");
    when(settings.version()).thenReturn("0.1.0");
    when(settings.applicationId()).thenReturn("SEGSENSE");

    SystemInfoService service = new SystemInfoService(healthPort, settings);

    SystemInfo info = service.current();
    assertThat(info.name()).isEqualTo("SegSense");
    assertThat(info.version()).isEqualTo("0.1.0");
    assertThat(info.applicationId()).isEqualTo("SEGSENSE");
    assertThat(info.operationalState()).isEqualTo(OperationalState.UP);
  }

  @Test
  void reportsDegradedWhenOperationalHealthPortIsDegraded() {
    OperationalHealthPort healthPort = mock(OperationalHealthPort.class);
    SatelliteSettings settings = mock(SatelliteSettings.class);
    when(healthPort.currentState()).thenReturn(OperationalState.DEGRADED);
    when(settings.name()).thenReturn("SegSense");
    when(settings.version()).thenReturn("0.1.0");
    when(settings.applicationId()).thenReturn("SEGSENSE");

    SystemInfoService service = new SystemInfoService(healthPort, settings);

    assertThat(service.current().operationalState()).isEqualTo(OperationalState.DEGRADED);
  }
}
