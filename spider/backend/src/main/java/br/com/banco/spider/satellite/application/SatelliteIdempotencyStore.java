package br.com.banco.spider.satellite.application;

import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;

final class SatelliteIdempotencyStore {

  private final ConcurrentHashMap<String, Stored> values = new ConcurrentHashMap<>();

  Stored get(String satelliteId, String key) {
    return values.get(satelliteId + ":" + key);
  }

  void put(String satelliteId, String key, Stored stored) {
    values.put(satelliteId + ":" + key, stored);
  }

  record Stored(String fingerprint, Map<String, Object> response) {
    boolean sameBody(String fingerprint) {
      return Objects.equals(bodyFingerprint(), fingerprint);
    }

    private String bodyFingerprint() {
      return fingerprint;
    }
  }
}
