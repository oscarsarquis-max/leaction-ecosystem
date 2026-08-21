package br.com.banco.spider.canonical.contract;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * Payload canônico mínimo. {@code canonicalData} é o único ponto flexível do núcleo.
 */
public record CanonicalPayload(JsonNode canonicalData) {

  public static CanonicalPayload of(JsonNode data) {
    return new CanonicalPayload(data);
  }

  public static CanonicalPayload empty() {
    return new CanonicalPayload(null);
  }
}
