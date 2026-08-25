package br.com.banco.spider.operational.failurelab;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.InputStream;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.core.io.ClassPathResource;

/**
 * Carrega e valida o catálogo versionado de cenários e runbooks. Falha rápido no bootstrap se o
 * catálogo estiver inconsistente — o Failure Lab não opera com catálogo parcial.
 */
public class FailureLabCatalogLoader {

  public static final String SCENARIOS_PATH = "implementation/failure-lab-scenarios-v1.json";
  public static final String RUNBOOKS_PATH = "implementation/failure-lab-runbooks-v1.json";

  private static final Duration MAX_SCENARIO_DURATION = Duration.ofMinutes(5);
  private static final int MAX_SCENARIO_EXECUTIONS = 10;
  private static final int MINIMUM_SCENARIOS = 17;

  private final List<FailureScenarioDefinition> scenarios;
  private final List<MockOperationalRunbook> runbooks;
  private final Map<String, FailureScenarioDefinition> scenariosByCode;
  private final Map<String, MockOperationalRunbook> runbooksByRef;

  public FailureLabCatalogLoader(ObjectMapper mapper) {
    List<FailureScenarioDefinition> loadedScenarios;
    List<MockOperationalRunbook> loadedRunbooks;
    try (InputStream scenariosInput = new ClassPathResource(SCENARIOS_PATH).getInputStream();
        InputStream runbooksInput = new ClassPathResource(RUNBOOKS_PATH).getInputStream()) {
      loadedScenarios =
          mapper.readValue(scenariosInput, new TypeReference<List<FailureScenarioDefinition>>() {});
      loadedRunbooks =
          mapper.readValue(runbooksInput, new TypeReference<List<MockOperationalRunbook>>() {});
    } catch (Exception failure) {
      throw new IllegalStateException("Could not load failure lab catalog", failure);
    }

    Map<String, MockOperationalRunbook> byRef = new LinkedHashMap<>();
    for (MockOperationalRunbook runbook : loadedRunbooks) {
      if (byRef.put(runbook.ref(), runbook) != null) {
        throw new IllegalStateException("Duplicate failure lab runbook ref: " + runbook.ref());
      }
    }

    Map<String, FailureScenarioDefinition> byCode = new LinkedHashMap<>();
    for (FailureScenarioDefinition scenario : loadedScenarios) {
      validate(scenario, byRef.keySet());
      if (byCode.put(scenario.code(), scenario) != null) {
        throw new IllegalStateException("Duplicate failure lab scenario code: " + scenario.code());
      }
    }
    if (byCode.size() < MINIMUM_SCENARIOS) {
      throw new IllegalStateException(
          "Failure lab catalog must declare at least " + MINIMUM_SCENARIOS + " scenarios");
    }

    this.scenarios = List.copyOf(loadedScenarios);
    this.runbooks = List.copyOf(loadedRunbooks);
    this.scenariosByCode = Map.copyOf(byCode);
    this.runbooksByRef = Map.copyOf(byRef);
  }

  private static void validate(
      FailureScenarioDefinition scenario, java.util.Set<String> knownRunbookRefs) {
    if (scenario.schemaVersion() != 1) {
      throw new IllegalStateException("Unsupported scenario schemaVersion: " + scenario.code());
    }
    if (scenario.expectedObservations().isEmpty()) {
      throw new IllegalStateException("Scenario declares no observations: " + scenario.code());
    }
    if (scenario.maximumDuration().compareTo(MAX_SCENARIO_DURATION) > 0) {
      throw new IllegalStateException("Scenario maximumDuration exceeds PT5M: " + scenario.code());
    }
    if (scenario.maximumExecutions() > MAX_SCENARIO_EXECUTIONS) {
      throw new IllegalStateException("Scenario maximumExecutions exceeds 10: " + scenario.code());
    }
    if (!knownRunbookRefs.contains(scenario.runbookRef())) {
      throw new IllegalStateException(
          "Scenario " + scenario.code() + " references unknown runbook " + scenario.runbookRef());
    }
    java.util.Set<String> observationCodes = new java.util.LinkedHashSet<>();
    for (ExpectedObservation observation : scenario.expectedObservations()) {
      if (!observationCodes.add(observation.code())) {
        throw new IllegalStateException(
            "Duplicate observation code in scenario " + scenario.code() + ": " + observation.code());
      }
    }
  }

  public List<FailureScenarioDefinition> scenarios() {
    return scenarios;
  }

  public List<MockOperationalRunbook> runbooks() {
    return runbooks;
  }

  public Optional<FailureScenarioDefinition> findScenario(String code, String version) {
    if (code == null || code.isBlank()) {
      return Optional.empty();
    }
    FailureScenarioDefinition scenario = scenariosByCode.get(code.trim());
    if (scenario == null) {
      return Optional.empty();
    }
    if (version != null && !version.isBlank() && !scenario.version().equals(version.trim())) {
      return Optional.empty();
    }
    return Optional.of(scenario);
  }

  public Optional<MockOperationalRunbook> findRunbook(String ref) {
    if (ref == null || ref.isBlank()) {
      return Optional.empty();
    }
    return Optional.ofNullable(runbooksByRef.get(ref.trim()));
  }
}
