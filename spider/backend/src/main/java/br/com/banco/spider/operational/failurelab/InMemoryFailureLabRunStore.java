package br.com.banco.spider.operational.failurelab;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/** Store em memória — o Failure Lab é ferramenta de demonstração, não SoR. */
public final class InMemoryFailureLabRunStore implements FailureLabRunStorePort {

  private static final int MAX_RETAINED_RUNS = 200;

  private final ConcurrentHashMap<String, FailureLabRun> runs = new ConcurrentHashMap<>();
  private final ConcurrentHashMap<String, FailureLabEvidenceBundle> evidence =
      new ConcurrentHashMap<>();

  @Override
  public void save(FailureLabRun run) {
    if (run == null) {
      return;
    }
    runs.put(run.labRunId(), run);
    evictOldest();
  }

  @Override
  public Optional<FailureLabRun> findById(String labRunId) {
    if (labRunId == null || labRunId.isBlank()) {
      return Optional.empty();
    }
    return Optional.ofNullable(runs.get(labRunId.trim()));
  }

  @Override
  public List<FailureLabRun> listRecent(int limit) {
    int effective = Math.max(1, Math.min(limit, MAX_RETAINED_RUNS));
    return runs.values().stream()
        .sorted(Comparator.comparing(FailureLabRun::requestedAt).reversed())
        .limit(effective)
        .toList();
  }

  @Override
  public void saveEvidence(FailureLabEvidenceBundle bundle) {
    if (bundle == null) {
      return;
    }
    evidence.put(bundle.labRunId(), bundle);
  }

  @Override
  public Optional<FailureLabEvidenceBundle> findEvidenceByRunId(String labRunId) {
    if (labRunId == null || labRunId.isBlank()) {
      return Optional.empty();
    }
    return Optional.ofNullable(evidence.get(labRunId.trim()));
  }

  private void evictOldest() {
    if (runs.size() <= MAX_RETAINED_RUNS) {
      return;
    }
    List<FailureLabRun> ordered = new ArrayList<>(runs.values());
    ordered.sort(Comparator.comparing(FailureLabRun::requestedAt));
    for (int i = 0; i < ordered.size() - MAX_RETAINED_RUNS; i++) {
      FailureLabRun stale = ordered.get(i);
      if (stale.status().isTerminal()) {
        runs.remove(stale.labRunId());
        evidence.remove(stale.labRunId());
      }
    }
  }
}
