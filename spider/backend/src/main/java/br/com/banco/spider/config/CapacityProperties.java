package br.com.banco.spider.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.capacity")
public class CapacityProperties {

  private boolean enabled = false;
  private final Http http = new Http();
  private final LocalDemo localDemo = new LocalDemo();
  private final Enforcement enforcement = new Enforcement();
  private int decisionLogSize = 200;

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

  public Enforcement getEnforcement() {
    return enforcement;
  }

  public int getDecisionLogSize() {
    return decisionLogSize;
  }

  public void setDecisionLogSize(int decisionLogSize) {
    this.decisionLogSize = decisionLogSize;
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

  public static class Enforcement {
    private boolean enabled = false;

    public boolean isEnabled() {
      return enabled;
    }

    public void setEnabled(boolean enabled) {
      this.enabled = enabled;
    }
  }
}
