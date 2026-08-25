package br.com.banco.spider.operational.failurelab;

import java.time.Duration;
import java.util.List;
import java.util.Objects;

/**
 * Definição declarativa de um cenário controlado de falha. Carregada de recurso versionado e
 * imutável em runtime; o Failure Lab nunca aceita cenário arbitrário vindo da borda.
 */
public record FailureScenarioDefinition(
    int schemaVersion,
    String code,
    String version,
    String title,
    String functionalDescription,
    FailureScenarioCategory category,
    String targetBoundary,
    List<String> preconditions,
    List<String> allowedParameterKeys,
    List<ExpectedObservation> expectedObservations,
    Duration maximumDuration,
    int maximumExecutions,
    String runbookRef,
    String mockScenario,
    String operationCode) {

  public static final String MOCK_ONLY = "MOCK_ONLY";

  public FailureScenarioDefinition {
    code = require("code", code);
    version = require("version", version);
    title = require("title", title);
    functionalDescription = functionalDescription == null ? "" : functionalDescription.trim();
    Objects.requireNonNull(category, "category");
    targetBoundary = targetBoundary == null ? MOCK_ONLY : targetBoundary.trim();
    if (!MOCK_ONLY.equals(targetBoundary)) {
      throw new IllegalArgumentException("targetBoundary must be MOCK_ONLY");
    }
    preconditions = preconditions == null ? List.of() : List.copyOf(preconditions);
    allowedParameterKeys =
        allowedParameterKeys == null ? List.of() : List.copyOf(allowedParameterKeys);
    expectedObservations =
        expectedObservations == null ? List.of() : List.copyOf(expectedObservations);
    Objects.requireNonNull(maximumDuration, "maximumDuration");
    if (maximumDuration.isNegative() || maximumDuration.isZero()) {
      throw new IllegalArgumentException("maximumDuration must be positive");
    }
    if (maximumExecutions < 0) {
      throw new IllegalArgumentException("maximumExecutions must not be negative");
    }
    runbookRef = require("runbookRef", runbookRef);
    mockScenario = blankToNull(mockScenario);
    operationCode = blankToNull(operationCode);
  }

  public String ref() {
    return code + "@" + version;
  }

  /** Cenários sem operação canônica não submetem execução à Engine. */
  public boolean requiresEngineSubmission() {
    return operationCode != null && mockScenario != null && maximumExecutions > 0;
  }

  private static String require(String name, String value) {
    Objects.requireNonNull(value, name);
    String trimmed = value.trim();
    if (trimmed.isEmpty()) {
      throw new IllegalArgumentException(name + " must not be blank");
    }
    return trimmed;
  }

  private static String blankToNull(String value) {
    if (value == null) {
      return null;
    }
    String trimmed = value.trim();
    return trimmed.isEmpty() ? null : trimmed;
  }
}
