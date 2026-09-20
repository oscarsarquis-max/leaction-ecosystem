package br.com.banco.spider.satellite.application;

import br.com.banco.spider.config.SatelliteContractProperties;
import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.config.SatelliteContractProperties.SatelliteEntry;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

public final class SatelliteRegistry {

  private final SatelliteContractProperties properties;

  public SatelliteRegistry(SatelliteContractProperties properties) {
    this.properties = properties;
  }

  public SatelliteEntry requireExperience(String satelliteId) {
    if (satelliteId == null || satelliteId.isBlank()) {
      return null;
    }
    SatelliteEntry entry = properties.getRegistry().get(satelliteId.toLowerCase(Locale.ROOT));
    if (entry == null || !"EXPERIENCE".equals(entry.getRole()) || !"ACTIVE".equals(entry.getStatus())) {
      return null;
    }
    return entry;
  }

  public String resolveSatelliteId(String satelliteIdOrAlias) {
    if (satelliteIdOrAlias == null || satelliteIdOrAlias.isBlank()) {
      return null;
    }
    String key = satelliteIdOrAlias.toLowerCase(Locale.ROOT);
    if (properties.getRegistry().containsKey(key)) {
      return key;
    }
    for (var entry : properties.getRegistry().entrySet()) {
      if (entry.getValue().getCredentialAliases().contains(satelliteIdOrAlias)) {
        return entry.getKey();
      }
    }
    return null;
  }

  public boolean secretMatches(SatelliteEntry entry, String provided) {
    String expected = entry.getSecret();
    if (expected == null || expected.isBlank()) {
      return false;
    }
    return MessageDigest.isEqual(sha256(expected), sha256(provided == null ? "" : provided));
  }

  public ProviderEntry resolveProvider(String capabilityId) {
    var binding = resolveProviderBinding(capabilityId);
    return binding == null ? null : binding.entry();
  }

  public ProviderBinding resolveProviderBinding(String capabilityId) {
    for (var registered : properties.getProviders().entrySet()) {
      ProviderEntry provider = registered.getValue();
      if (!"PROVIDER".equals(provider.getRole())) {
        continue;
      }
      if (!"TEST_DOUBLE".equals(provider.getStatus()) && !"ACTIVE".equals(provider.getStatus())) {
        continue;
      }
      if (provider.getCapabilities().contains(capabilityId)) {
        return new ProviderBinding(registered.getKey(), provider);
      }
    }
    return null;
  }

  public record ProviderBinding(String providerId, ProviderEntry entry) {}

  public SatelliteContractProperties properties() {
    return properties;
  }

  private static byte[] sha256(String value) {
    try {
      return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }
}
