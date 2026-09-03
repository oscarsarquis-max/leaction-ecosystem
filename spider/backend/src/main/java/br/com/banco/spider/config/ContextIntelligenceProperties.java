package br.com.banco.spider.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.context")
public class ContextIntelligenceProperties {

  private boolean enabled;
  private final Ui ui = new Ui();

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public Ui getUi() {
    return ui;
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
}
