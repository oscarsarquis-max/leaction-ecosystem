package br.com.banco.spider.integration.inbound.http.satellite;

import br.com.banco.spider.config.SatelliteContractProperties.SatelliteEntry;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public final class SatelliteApplicationAuth {

  public static final String SATELLITE_ID_HEADER = "X-Spider-Satellite-Id";
  public static final String SATELLITE_SECRET_HEADER = "X-Spider-Satellite-Secret";

  private final SatelliteRegistry registry;

  public SatelliteApplicationAuth(SatelliteRegistry registry) {
    this.registry = registry;
  }

  public String authenticate(String satelliteIdHeader, String secret) {
    String satelliteId = registry.resolveSatelliteId(satelliteIdHeader);
    if (satelliteId == null) {
      return null;
    }
    SatelliteEntry entry = registry.requireExperience(satelliteId);
    if (entry == null) {
      return null;
    }
    if (!registry.secretMatches(entry, secret)) {
      return null;
    }
    return satelliteId;
  }

  public static boolean secretsEqual(String expected, String provided) {
    if (expected == null || expected.isBlank()) {
      return false;
    }
    try {
      return MessageDigest.isEqual(
          MessageDigest.getInstance("SHA-256").digest(expected.getBytes(StandardCharsets.UTF_8)),
          MessageDigest.getInstance("SHA-256")
              .digest((provided == null ? "" : provided).getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }
}
