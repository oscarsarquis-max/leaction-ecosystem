package br.com.banco.spider.operational.failurelab;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Leitura segura do catálogo, das execuções controladas e das evidências. */
public class FailureLabQueryService {

  private final FailureLabCatalogLoader catalog;
  private final FailureLabRunStorePort store;

  public FailureLabQueryService(FailureLabCatalogLoader catalog, FailureLabRunStorePort store) {
    this.catalog = catalog;
    this.store = store;
  }

  public Map<String, Object> listScenarios() {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("schemaVersion", 1);
    body.put("boundary", FailureScenarioDefinition.MOCK_ONLY);
    body.put("scenarios", catalog.scenarios());
    body.put("runbooks", catalog.runbooks());
    return Map.copyOf(body);
  }

  public Optional<FailureLabRun> getRun(String labRunId) {
    return store.findById(labRunId).map(FailureLabQueryService::redact);
  }

  public List<FailureLabRun> listRecentRuns(int limit) {
    return store.listRecent(limit).stream().map(FailureLabQueryService::redact).toList();
  }

  public Optional<FailureLabEvidenceBundle> getEvidence(String labRunId) {
    return store.findEvidenceByRunId(labRunId);
  }

  private static FailureLabRun redact(FailureLabRun run) {
    Map<String, String> safeParameters = FailureLabRedaction.sanitize(run.parameters());
    if (safeParameters.size() == run.parameters().size()) {
      return run;
    }
    return new FailureLabRun(
        run.schemaVersion(),
        run.labRunId(),
        run.scenarioCode(),
        run.scenarioVersion(),
        run.requestedAt(),
        run.requestedBy(),
        run.startedAt(),
        run.completedAt(),
        run.status(),
        run.boundary(),
        safeParameters,
        run.executionRefs(),
        run.verificationResults(),
        run.evidenceSummary(),
        run.failureMessage());
  }
}
