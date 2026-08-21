package br.com.banco.spider.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.console")
public class OperationalConsoleProperties {

  private boolean enabled = false;
  private final Http http = new Http();
  private final LocalDemo localDemo = new LocalDemo();
  private int maxPageSize = 50;
  private int defaultPageSize = 20;
  private Duration pollingMinInterval = Duration.ofSeconds(1);
  private final SafeProjections safeProjections = new SafeProjections();

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public Http getHttp() {
    return http;
  }

  public LocalDemo getLocalDemo() {
    return localDemo;
  }

  public int getMaxPageSize() {
    return maxPageSize;
  }

  public void setMaxPageSize(int maxPageSize) {
    this.maxPageSize = maxPageSize;
  }

  public int getDefaultPageSize() {
    return defaultPageSize;
  }

  public void setDefaultPageSize(int defaultPageSize) {
    this.defaultPageSize = defaultPageSize;
  }

  public Duration getPollingMinInterval() {
    return pollingMinInterval;
  }

  public void setPollingMinInterval(Duration pollingMinInterval) {
    this.pollingMinInterval = pollingMinInterval;
  }

  public SafeProjections getSafeProjections() {
    return safeProjections;
  }

  public static class Http {
    private boolean enabled = false;

    public boolean isEnabled() {
      return enabled;
    }

    public void setEnabled(boolean enabled) {
      this.enabled = enabled;
    }
  }

  public static class LocalDemo {
    private boolean enabled = false;

    public boolean isEnabled() {
      return enabled;
    }

    public void setEnabled(boolean enabled) {
      this.enabled = enabled;
    }
  }

  public static class SafeProjections {
    private boolean enabled = false;

    public boolean isEnabled() {
      return enabled;
    }

    public void setEnabled(boolean enabled) {
      this.enabled = enabled;
    }
  }
}
