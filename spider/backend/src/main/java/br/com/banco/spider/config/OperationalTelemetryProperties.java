package br.com.banco.spider.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("spider.telemetry")
public class OperationalTelemetryProperties {

  private boolean enabled = false;

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }
}
