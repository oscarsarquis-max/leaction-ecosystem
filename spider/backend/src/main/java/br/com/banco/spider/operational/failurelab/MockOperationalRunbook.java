package br.com.banco.spider.operational.failurelab;

import java.util.List;
import java.util.Objects;

/**
 * Runbook operacional provisório (MOCK_ONLY). Texto funcional em português, sem procedimento de
 * produção e sem referência a sistema real.
 */
public record MockOperationalRunbook(
    int schemaVersion,
    String code,
    String version,
    String title,
    String purpose,
    List<String> applicableScenarioRefs,
    List<String> symptoms,
    List<String> checks,
    List<String> expectedEvidence,
    List<String> safeActions,
    List<String> stopConditions,
    String escalationGuidance,
    String limitations) {

  public MockOperationalRunbook {
    Objects.requireNonNull(code, "code");
    Objects.requireNonNull(version, "version");
    Objects.requireNonNull(title, "title");
    purpose = purpose == null ? "" : purpose;
    applicableScenarioRefs =
        applicableScenarioRefs == null ? List.of() : List.copyOf(applicableScenarioRefs);
    symptoms = symptoms == null ? List.of() : List.copyOf(symptoms);
    checks = checks == null ? List.of() : List.copyOf(checks);
    expectedEvidence = expectedEvidence == null ? List.of() : List.copyOf(expectedEvidence);
    safeActions = safeActions == null ? List.of() : List.copyOf(safeActions);
    stopConditions = stopConditions == null ? List.of() : List.copyOf(stopConditions);
    escalationGuidance = escalationGuidance == null ? "" : escalationGuidance;
    limitations = limitations == null ? "" : limitations;
  }

  public String ref() {
    return code + "@" + version;
  }
}
