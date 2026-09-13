package br.com.segsense.inbound.http.consent;

import java.util.List;

public record ContextInstanceValuesRequest(Long expectedVersion, List<CollectedValueRequest> values) {

  public record CollectedValueRequest(String key, String type, Object value) {}
}
