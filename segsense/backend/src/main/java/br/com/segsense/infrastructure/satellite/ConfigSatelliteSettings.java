package br.com.segsense.infrastructure.satellite;

import br.com.segsense.application.satellite.SatelliteSettings;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ConfigSatelliteSettings implements SatelliteSettings {

  private final String applicationId;
  private final String name;
  private final String version;

  public ConfigSatelliteSettings(
      @Value("${segsense.satellite.application-id}") String applicationId,
      @Value("${segsense.app.name}") String name,
      @Value("${segsense.app.version}") String version) {
    this.applicationId = applicationId;
    this.name = name;
    this.version = version;
  }

  @Override
  public String applicationId() {
    return applicationId;
  }

  @Override
  public String name() {
    return name;
  }

  @Override
  public String version() {
    return version;
  }
}
