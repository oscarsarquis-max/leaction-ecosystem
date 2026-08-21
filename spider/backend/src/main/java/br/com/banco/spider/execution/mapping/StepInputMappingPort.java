package br.com.banco.spider.execution.mapping;

import br.com.banco.spider.canonical.error.CanonicalError;
import com.fasterxml.jackson.databind.JsonNode;

public interface StepInputMappingPort {
  MappingResult map(MappingRequest request);

  record MappingRequest(
      StepInputMappingKind kind, JsonNode rootCanonicalData, JsonNode previousStepCanonicalData) {}

  record MappingResult(boolean success, JsonNode canonicalData, CanonicalError error) {
    public static MappingResult ok(JsonNode data) {
      return new MappingResult(true, data, null);
    }

    public static MappingResult fail(CanonicalError error) {
      return new MappingResult(false, null, error);
    }
  }
}
