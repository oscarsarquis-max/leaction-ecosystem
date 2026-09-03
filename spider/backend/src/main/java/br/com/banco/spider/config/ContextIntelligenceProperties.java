package br.com.banco.spider.config;

import java.math.BigDecimal;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.context")
public class ContextIntelligenceProperties {

  private boolean enabled;
  private final Ui ui = new Ui();
  private final Ai ai = new Ai();

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public Ui getUi() {
    return ui;
  }

  public Ai getAi() {
    return ai;
  }

  public static final class Ui {
    private boolean enabled;

    public boolean isEnabled() {
      return enabled;
    }

    public void setEnabled(boolean enabled) {
      this.enabled = enabled;
    }
  }

  public static final class Ai {
    private boolean enabled;
    private String provider = "bedrock";
    private String model = "anthropic.claude-3-5-haiku-20241022-v1:0";
    private String region = "us-east-1";
    private Duration timeout = Duration.ofSeconds(8);
    private BigDecimal minimumConfidence = new BigDecimal("0.80");
    private int maxInputChars = 2000;
    private boolean scriptedEnabled;

    public boolean isEnabled() {
      return enabled;
    }

    public void setEnabled(boolean enabled) {
      this.enabled = enabled;
    }

    public String getProvider() {
      return provider;
    }

    public void setProvider(String provider) {
      this.provider = provider;
    }

    public String getModel() {
      return model;
    }

    public void setModel(String model) {
      this.model = model;
    }

    public String getRegion() {
      return region;
    }

    public void setRegion(String region) {
      this.region = region;
    }

    public Duration getTimeout() {
      return timeout;
    }

    public void setTimeout(Duration timeout) {
      this.timeout = timeout;
    }

    public BigDecimal getMinimumConfidence() {
      return minimumConfidence;
    }

    public void setMinimumConfidence(BigDecimal minimumConfidence) {
      this.minimumConfidence = minimumConfidence;
    }

    public int getMaxInputChars() {
      return maxInputChars;
    }

    public void setMaxInputChars(int maxInputChars) {
      this.maxInputChars = maxInputChars;
    }

    public boolean isScriptedEnabled() {
      return scriptedEnabled;
    }

    public void setScriptedEnabled(boolean scriptedEnabled) {
      this.scriptedEnabled = scriptedEnabled;
    }
  }
}
