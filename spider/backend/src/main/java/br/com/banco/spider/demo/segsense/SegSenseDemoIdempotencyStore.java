package br.com.banco.spider.demo.segsense;

import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;

final class SegSenseDemoIdempotencyStore {

  private final ConcurrentHashMap<String, Stored> values = new ConcurrentHashMap<>();

  Stored get(String key) {
    return values.get(key);
  }

  void put(String key, Stored stored) {
    values.put(key, stored);
  }

  record Stored(String bodyFingerprint, Map<String, Object> response) {
    boolean sameBody(String fingerprint) {
      return Objects.equals(bodyFingerprint, fingerprint);
    }
  }
}
