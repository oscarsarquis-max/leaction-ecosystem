package br.com.banco.spider.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.canonical.http")
public class CanonicalHttpProperties {

  /** Gate técnico transitório — não é Control Plane. Default false. */
  private boolean enabled = false;

  private boolean statusQueryEnabled = false;

  private long maxRequestBytes = 65536;

  private long maxCanonicalDataBytes = 32768;

  private Duration requestTimeout = Duration.ofSeconds(30);

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public boolean isStatusQueryEnabled() {
    return statusQueryEnabled;
  }

  public void setStatusQueryEnabled(boolean statusQueryEnabled) {
    this.statusQueryEnabled = statusQueryEnabled;
  }

  public long getMaxRequestBytes() {
    return maxRequestBytes;
  }

  public void setMaxRequestBytes(long maxRequestBytes) {
    if (maxRequestBytes < 1024 || maxRequestBytes > 10_485_760) {
      throw new IllegalArgumentException("maxRequestBytes out of safe range");
    }
    this.maxRequestBytes = maxRequestBytes;
  }

  public long getMaxCanonicalDataBytes() {
    return maxCanonicalDataBytes;
  }

  public void setMaxCanonicalDataBytes(long maxCanonicalDataBytes) {
    if (maxCanonicalDataBytes < 512 || maxCanonicalDataBytes > 5_242_880) {
      throw new IllegalArgumentException("maxCanonicalDataBytes out of safe range");
    }
    this.maxCanonicalDataBytes = maxCanonicalDataBytes;
  }

  public Duration getRequestTimeout() {
    return requestTimeout;
  }

  public void setRequestTimeout(Duration requestTimeout) {
    if (requestTimeout == null || requestTimeout.isNegative() || requestTimeout.isZero()) {
      throw new IllegalArgumentException("requestTimeout must be positive");
    }
    this.requestTimeout = requestTimeout;
  }
}
