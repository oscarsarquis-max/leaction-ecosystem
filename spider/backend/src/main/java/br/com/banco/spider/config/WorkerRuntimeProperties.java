package br.com.banco.spider.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.worker-runtime")
public class WorkerRuntimeProperties {

  private boolean enabled = false;
  private final Http http = new Http();
  private final LocalDemo localDemo = new LocalDemo();
  private final Recovery recovery = new Recovery();
  private String instanceId = "";
  private Duration heartbeatInterval = Duration.ofSeconds(5);
  private Duration staleAfter = Duration.ofSeconds(20);
  private Duration tickInterval = Duration.ofSeconds(1);
  private int defaultBatchSize = 25;
  private Duration defaultLeaseDuration = Duration.ofSeconds(30);
  private Duration defaultExecutionTimeout = Duration.ofSeconds(20);
  private int maxConcurrency = 4;
  private Duration drainTimeout = Duration.ofSeconds(30);
  private int maxAttempts = 3;
  private boolean allowDrain = false;

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

  public Recovery getRecovery() {
    return recovery;
  }

  public String getInstanceId() {
    return instanceId;
  }

  public void setInstanceId(String instanceId) {
    this.instanceId = instanceId;
  }

  public Duration getHeartbeatInterval() {
    return heartbeatInterval;
  }

  public void setHeartbeatInterval(Duration heartbeatInterval) {
    this.heartbeatInterval = heartbeatInterval;
  }

  public Duration getStaleAfter() {
    return staleAfter;
  }

  public void setStaleAfter(Duration staleAfter) {
    this.staleAfter = staleAfter;
  }

  public Duration getTickInterval() {
    return tickInterval;
  }

  public void setTickInterval(Duration tickInterval) {
    this.tickInterval = tickInterval;
  }

  public int getDefaultBatchSize() {
    return defaultBatchSize;
  }

  public void setDefaultBatchSize(int defaultBatchSize) {
    this.defaultBatchSize = defaultBatchSize;
  }

  public Duration getDefaultLeaseDuration() {
    return defaultLeaseDuration;
  }

  public void setDefaultLeaseDuration(Duration defaultLeaseDuration) {
    this.defaultLeaseDuration = defaultLeaseDuration;
  }

  public Duration getDefaultExecutionTimeout() {
    return defaultExecutionTimeout;
  }

  public void setDefaultExecutionTimeout(Duration defaultExecutionTimeout) {
    this.defaultExecutionTimeout = defaultExecutionTimeout;
  }

  public int getMaxConcurrency() {
    return maxConcurrency;
  }

  public void setMaxConcurrency(int maxConcurrency) {
    this.maxConcurrency = maxConcurrency;
  }

  public Duration getDrainTimeout() {
    return drainTimeout;
  }

  public void setDrainTimeout(Duration drainTimeout) {
    this.drainTimeout = drainTimeout;
  }

  public int getMaxAttempts() {
    return maxAttempts;
  }

  public void setMaxAttempts(int maxAttempts) {
    this.maxAttempts = maxAttempts;
  }

  public boolean isAllowDrain() {
    return allowDrain;
  }

  public void setAllowDrain(boolean allowDrain) {
    this.allowDrain = allowDrain;
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

  public static class Recovery {
    private boolean enabled = false;

    public boolean isEnabled() {
      return enabled;
    }

    public void setEnabled(boolean enabled) {
      this.enabled = enabled;
    }
  }
}
