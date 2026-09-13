package br.com.segsense.application.system;

import br.com.segsense.application.satellite.SatelliteSettings;
import br.com.segsense.domain.system.SystemInfo;
import org.springframework.stereotype.Service;

@Service
public class SystemInfoService {

  private final OperationalHealthPort operationalHealthPort;
  private final SatelliteSettings satelliteSettings;

  public SystemInfoService(
      OperationalHealthPort operationalHealthPort, SatelliteSettings satelliteSettings) {
    this.operationalHealthPort = operationalHealthPort;
    this.satelliteSettings = satelliteSettings;
  }

  public SystemInfo current() {
    return new SystemInfo(
        satelliteSettings.name(),
        satelliteSettings.version(),
        satelliteSettings.applicationId(),
        operationalHealthPort.currentState());
  }
}
