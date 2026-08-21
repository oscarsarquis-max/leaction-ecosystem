package br.com.banco.spider.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.canonical.signal-http")
public class CanonicalSignalHttpProperties {

  private boolean enabled = false;
  private long maxRequestBytes = 32768;

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public long getMaxRequestBytes() {
    return maxRequestBytes;
  }

  public void setMaxRequestBytes(long maxRequestBytes) {
    if (maxRequestBytes < 1024 || maxRequestBytes > 5_242_880) {
      throw new IllegalArgumentException("signal maxRequestBytes out of safe range");
    }
    this.maxRequestBytes = maxRequestBytes;
  }
}
