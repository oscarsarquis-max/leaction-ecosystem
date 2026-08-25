package br.com.banco.spider.config;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("spider.operational-health")
public class OperationalHealthProperties {
  private boolean enabled = false;
  private Duration defaultWindow = Duration.ofHours(24);
  private Duration maxWindow = Duration.ofDays(7);
  private List<Duration> allowedWindows =
      new ArrayList<>(
          List.of(
              Duration.ofMinutes(15),
              Duration.ofHours(1),
              Duration.ofHours(24),
              Duration.ofDays(7)));
  private int minimumSampleSize = 20;
  private int maxResults = 5000;
  private Duration agedWaitThreshold = Duration.ofMinutes(5);

  public boolean isEnabled() { return enabled; }
  public void setEnabled(boolean enabled) { this.enabled = enabled; }
  public Duration getDefaultWindow() { return defaultWindow; }
  public void setDefaultWindow(Duration defaultWindow) { this.defaultWindow = defaultWindow; }
  public Duration getMaxWindow() { return maxWindow; }
  public void setMaxWindow(Duration maxWindow) { this.maxWindow = maxWindow; }
  public List<Duration> getAllowedWindows() { return allowedWindows; }
  public void setAllowedWindows(List<Duration> allowedWindows) { this.allowedWindows = allowedWindows; }
  public int getMinimumSampleSize() { return minimumSampleSize; }
  public void setMinimumSampleSize(int minimumSampleSize) { this.minimumSampleSize = minimumSampleSize; }
  public int getMaxResults() { return maxResults; }
  public void setMaxResults(int maxResults) { this.maxResults = maxResults; }
  public Duration getAgedWaitThreshold() { return agedWaitThreshold; }
  public void setAgedWaitThreshold(Duration agedWaitThreshold) { this.agedWaitThreshold = agedWaitThreshold; }
}
