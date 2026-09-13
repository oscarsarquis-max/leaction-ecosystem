package br.com.segsense.application.satellite;

public final class SatelliteIdentityGuard {

  private SatelliteIdentityGuard() {}

  public static void requireMatching(String configuredApplicationId, String manifestApplicationId) {
    if (configuredApplicationId == null
        || manifestApplicationId == null
        || !configuredApplicationId.equals(manifestApplicationId)) {
      throw new IllegalStateException(
          "Satellite manifest applicationId does not match local configuration");
    }
  }
}
