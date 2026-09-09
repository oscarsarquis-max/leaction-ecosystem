package br.com.banco.spider.config;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.demo.contextual-link")
public class ContextualLinkProperties {

  private boolean enabled = false;
  private String gatewayPath = "/go";
  private String spiderbankEntryUrl = "http://127.0.0.1:5180/spiderbank";
  private String partnerPublicName = "CampoAberto";
  private String publicBaseUrl = "http://127.0.0.1:8080";
  private Acquisition acquisition = new Acquisition();

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public String getGatewayPath() {
    return gatewayPath;
  }

  public void setGatewayPath(String gatewayPath) {
    this.gatewayPath = gatewayPath;
  }

  public String getSpiderbankEntryUrl() {
    return spiderbankEntryUrl;
  }

  public void setSpiderbankEntryUrl(String spiderbankEntryUrl) {
    this.spiderbankEntryUrl = spiderbankEntryUrl;
  }

  public String spiderbankEntryUrl() {
    return spiderbankEntryUrl;
  }

  public String getPartnerPublicName() {
    return partnerPublicName;
  }

  public void setPartnerPublicName(String partnerPublicName) {
    this.partnerPublicName = partnerPublicName;
  }

  public String getPublicBaseUrl() {
    return publicBaseUrl;
  }

  public void setPublicBaseUrl(String publicBaseUrl) {
    this.publicBaseUrl = publicBaseUrl;
  }

  public String gatewayPublicUrl() {
    String base = publicBaseUrl.endsWith("/") ? publicBaseUrl.substring(0, publicBaseUrl.length() - 1) : publicBaseUrl;
    String path = gatewayPath.startsWith("/") ? gatewayPath : "/" + gatewayPath;
    return base + path;
  }

  public Acquisition getAcquisition() {
    return acquisition;
  }

  public void setAcquisition(Acquisition acquisition) {
    this.acquisition = acquisition;
  }

  public static class Acquisition {
    private List<String> allowedOrigins = new ArrayList<>();
    private List<String> allowedPathPrefixes = new ArrayList<>();
    private int maxBytes = 262144;
    private Duration timeout = Duration.ofSeconds(3);

    public List<String> getAllowedOrigins() {
      return allowedOrigins;
    }

    public void setAllowedOrigins(List<String> allowedOrigins) {
      this.allowedOrigins = allowedOrigins;
    }

    public List<String> getAllowedPathPrefixes() {
      return allowedPathPrefixes;
    }

    public void setAllowedPathPrefixes(List<String> allowedPathPrefixes) {
      this.allowedPathPrefixes = allowedPathPrefixes;
    }

    public int getMaxBytes() {
      return maxBytes;
    }

    public void setMaxBytes(int maxBytes) {
      this.maxBytes = maxBytes;
    }

    public Duration getTimeout() {
      return timeout;
    }

    public void setTimeout(Duration timeout) {
      this.timeout = timeout;
    }
  }
}
