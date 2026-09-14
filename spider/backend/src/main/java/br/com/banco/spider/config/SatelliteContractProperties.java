package br.com.banco.spider.config;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "spider.satellite")
public class SatelliteContractProperties {

  private boolean enabled = false;
  private int maxBytes = 8192;
  private boolean loopbackOnly = true;
  private Map<String, SatelliteEntry> registry = new LinkedHashMap<>();
  private Map<String, ProviderEntry> providers = new LinkedHashMap<>();

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public int getMaxBytes() {
    return maxBytes;
  }

  public void setMaxBytes(int maxBytes) {
    this.maxBytes = maxBytes;
  }

  public boolean isLoopbackOnly() {
    return loopbackOnly;
  }

  public void setLoopbackOnly(boolean loopbackOnly) {
    this.loopbackOnly = loopbackOnly;
  }

  public Map<String, SatelliteEntry> getRegistry() {
    return registry;
  }

  public void setRegistry(Map<String, SatelliteEntry> registry) {
    this.registry = registry == null ? new LinkedHashMap<>() : registry;
  }

  public Map<String, ProviderEntry> getProviders() {
    return providers;
  }

  public void setProviders(Map<String, ProviderEntry> providers) {
    this.providers = providers == null ? new LinkedHashMap<>() : providers;
  }

  public static class SatelliteEntry {
    private String role = "EXPERIENCE";
    private String secret = "";
    private List<String> credentialAliases = new ArrayList<>();
    private List<String> purposes = new ArrayList<>();
    private List<String> interactionTypes = new ArrayList<>();
    private List<String> classifications = new ArrayList<>();
    private List<String> governedContextIds = new ArrayList<>();
    private List<String> declaredContextIds = new ArrayList<>();
    private List<String> allowedObjectives = new ArrayList<>();
    private Map<String, List<String>> allowedAttributes = new LinkedHashMap<>();
    private String environment = "local-demo";
    private String status = "ACTIVE";

    public String getRole() {
      return role;
    }

    public void setRole(String role) {
      this.role = role;
    }

    public String getSecret() {
      return secret;
    }

    public void setSecret(String secret) {
      this.secret = secret;
    }

    public List<String> getCredentialAliases() {
      return credentialAliases;
    }

    public void setCredentialAliases(List<String> credentialAliases) {
      this.credentialAliases = credentialAliases == null ? new ArrayList<>() : credentialAliases;
    }

    public List<String> getPurposes() {
      return purposes;
    }

    public void setPurposes(List<String> purposes) {
      this.purposes = purposes == null ? new ArrayList<>() : purposes;
    }

    public List<String> getInteractionTypes() {
      return interactionTypes;
    }

    public void setInteractionTypes(List<String> interactionTypes) {
      this.interactionTypes = interactionTypes == null ? new ArrayList<>() : interactionTypes;
    }

    public List<String> getClassifications() {
      return classifications;
    }

    public void setClassifications(List<String> classifications) {
      this.classifications = classifications == null ? new ArrayList<>() : classifications;
    }

    public List<String> getGovernedContextIds() {
      return governedContextIds;
    }

    public void setGovernedContextIds(List<String> governedContextIds) {
      this.governedContextIds = governedContextIds == null ? new ArrayList<>() : governedContextIds;
    }

    public List<String> getDeclaredContextIds() {
      return declaredContextIds;
    }

    public void setDeclaredContextIds(List<String> declaredContextIds) {
      this.declaredContextIds = declaredContextIds == null ? new ArrayList<>() : declaredContextIds;
    }

    public List<String> getAllowedObjectives() {
      return allowedObjectives;
    }

    public void setAllowedObjectives(List<String> allowedObjectives) {
      this.allowedObjectives = allowedObjectives == null ? new ArrayList<>() : allowedObjectives;
    }

    public Map<String, List<String>> getAllowedAttributes() {
      return allowedAttributes;
    }

    public void setAllowedAttributes(Map<String, List<String>> allowedAttributes) {
      this.allowedAttributes = allowedAttributes == null ? new LinkedHashMap<>() : allowedAttributes;
    }

    public String getEnvironment() {
      return environment;
    }

    public void setEnvironment(String environment) {
      this.environment = environment;
    }

    public String getStatus() {
      return status;
    }

    public void setStatus(String status) {
      this.status = status;
    }
  }

  public static class ProviderEntry {
    private String role = "PROVIDER";
    private String status = "TEST_DOUBLE";
    private String environment = "local-demo";
    private List<String> contractVersions = new ArrayList<>(List.of("1.0"));
    private List<String> capabilities = new ArrayList<>();
    private String baseUrl = "http://127.0.0.1:8095";
    private String secret = "";
    private Duration timeout = Duration.ofSeconds(3);

    public String getRole() {
      return role;
    }

    public void setRole(String role) {
      this.role = role;
    }

    public String getStatus() {
      return status;
    }

    public void setStatus(String status) {
      this.status = status;
    }

    public String getEnvironment() {
      return environment;
    }

    public void setEnvironment(String environment) {
      this.environment = environment;
    }

    public List<String> getContractVersions() {
      return contractVersions;
    }

    public void setContractVersions(List<String> contractVersions) {
      this.contractVersions = contractVersions == null ? new ArrayList<>() : contractVersions;
    }

    public List<String> getCapabilities() {
      return capabilities;
    }

    public void setCapabilities(List<String> capabilities) {
      this.capabilities = capabilities == null ? new ArrayList<>() : capabilities;
    }

    public String getBaseUrl() {
      return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
      this.baseUrl = baseUrl;
    }

    public String getSecret() {
      return secret;
    }

    public void setSecret(String secret) {
      this.secret = secret;
    }

    public Duration getTimeout() {
      return timeout;
    }

    public void setTimeout(Duration timeout) {
      this.timeout = timeout;
    }
  }
}
