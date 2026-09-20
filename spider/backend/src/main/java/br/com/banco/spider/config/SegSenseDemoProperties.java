package br.com.banco.spider.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.demo.segsense")
public class SegSenseDemoProperties {

  private boolean enabled = false;
  /** Public application identity. Not a secret. */
  private String credentialRef = "local-demo-segsense";
  /** Shared secret from unversioned env. Empty means fail-closed. */
  private String applicationSecret = "";
  private String mockBaseUrl = "http://127.0.0.1:8095";
  private String productUrl = "http://127.0.0.1:5178/demonstracao/mvp-integrado";
  private String mockCredential = "";
  private Duration timeout = Duration.ofSeconds(3);
  private int maxBytes = 8192;

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public String getCredentialRef() {
    return credentialRef;
  }

  public void setCredentialRef(String credentialRef) {
    this.credentialRef = credentialRef;
  }

  public String getApplicationSecret() {
    return applicationSecret;
  }

  public void setApplicationSecret(String applicationSecret) {
    this.applicationSecret = applicationSecret;
  }

  public String getMockBaseUrl() {
    return mockBaseUrl;
  }

  public void setMockBaseUrl(String mockBaseUrl) {
    this.mockBaseUrl = mockBaseUrl;
  }

  public String getProductUrl() {
    return productUrl;
  }

  public void setProductUrl(String productUrl) {
    this.productUrl = productUrl;
  }

  public String getMockCredential() {
    return mockCredential;
  }

  public void setMockCredential(String mockCredential) {
    this.mockCredential = mockCredential;
  }

  public Duration getTimeout() {
    return timeout;
  }

  public void setTimeout(Duration timeout) {
    this.timeout = timeout;
  }

  public int getMaxBytes() {
    return maxBytes;
  }

  public void setMaxBytes(int maxBytes) {
    this.maxBytes = maxBytes;
  }
}
