package br.com.banco.spider.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.credit-demo")
public class CreditDemoProperties {

  private boolean enabled = false;
  private String productUrl = "http://127.0.0.1:5190/";
  private String bffUrl = "http://127.0.0.1:8090/api/health";
  private String mockBaseUrl = "http://127.0.0.1:8096";
  private String assertionSecret = "";

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public String getProductUrl() {
    return productUrl;
  }

  public void setProductUrl(String productUrl) {
    this.productUrl = productUrl;
  }

  public String getBffUrl() {
    return bffUrl;
  }

  public void setBffUrl(String bffUrl) {
    this.bffUrl = bffUrl;
  }

  public String getMockBaseUrl() {
    return mockBaseUrl;
  }

  public void setMockBaseUrl(String mockBaseUrl) {
    this.mockBaseUrl = mockBaseUrl;
  }

  public String getAssertionSecret() {
    return assertionSecret;
  }

  public void setAssertionSecret(String assertionSecret) {
    this.assertionSecret = assertionSecret;
  }
}
