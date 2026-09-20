package br.com.spiderbank.application;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

@Component
public class InMemoryJourneyStore {

  private final ConcurrentHashMap<String, Map<String, Object>> responses = new ConcurrentHashMap<>();
  private final ConcurrentHashMap<String, String> fingerprints = new ConcurrentHashMap<>();

  public Map<String, Object> get(String idempotencyKey) {
    return responses.get(idempotencyKey);
  }

  public String fingerprint(String idempotencyKey) {
    return fingerprints.get(idempotencyKey);
  }

  public void put(String idempotencyKey, String fingerprint, Map<String, Object> response) {
    fingerprints.put(idempotencyKey, fingerprint);
    responses.put(idempotencyKey, response);
  }
}
