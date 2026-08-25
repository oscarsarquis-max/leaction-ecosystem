package br.com.banco.spider.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.failure-lab")
public class FailureLabProperties {

  private boolean enabled = false;
  private final Http http = new Http();
  private final LocalDemo localDemo = new LocalDemo();
  private int maxConcurrentRuns = 1;
  private int maxExecutionsPerRun = 10;
  private Duration maxRunDuration = Duration.ofMinutes(5);
  private final Evidence evidence = new Evidence();

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

  public int getMaxConcurrentRuns() {
    return maxConcurrentRuns;
  }

  public void setMaxConcurrentRuns(int maxConcurrentRuns) {
    this.maxConcurrentRuns = maxConcurrentRuns;
  }

  public int getMaxExecutionsPerRun() {
    return maxExecutionsPerRun;
  }

  public void setMaxExecutionsPerRun(int maxExecutionsPerRun) {
    this.maxExecutionsPerRun = maxExecutionsPerRun;
  }

  public Duration getMaxRunDuration() {
    return maxRunDuration;
  }

  public void setMaxRunDuration(Duration maxRunDuration) {
    this.maxRunDuration = maxRunDuration;
  }

  public Evidence getEvidence() {
    return evidence;
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

  public static class Evidence {
    private boolean enabled = true;

    public boolean isEnabled() {
      return enabled;
    }

    public void setEnabled(boolean enabled) {
      this.enabled = enabled;
    }
  }
}
