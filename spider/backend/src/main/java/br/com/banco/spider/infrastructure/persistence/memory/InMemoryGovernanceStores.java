package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.GovernanceActivation;
import br.com.banco.spider.governance.GovernanceArtifact;
import br.com.banco.spider.governance.GovernanceArtifactRef;
import br.com.banco.spider.governance.GovernanceArtifactType;
import br.com.banco.spider.governance.GovernanceAuditEvent;
import br.com.banco.spider.governance.GovernanceBundle;
import br.com.banco.spider.governance.GovernanceScope;
import br.com.banco.spider.governance.GovernanceValidationReport;
import br.com.banco.spider.governance.port.GovernanceActivationStorePort;
import br.com.banco.spider.governance.port.GovernanceArtifactStorePort;
import br.com.banco.spider.governance.port.GovernanceAuditStorePort;
import br.com.banco.spider.governance.port.GovernanceBundleStorePort;
import br.com.banco.spider.governance.port.GovernanceSnapshotStorePort;
import br.com.banco.spider.governance.port.GovernanceValidationReportStorePort;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/** Stores de governança em memória — um facade para testes e mode memory. */
public class InMemoryGovernanceStores
    implements GovernanceArtifactStorePort,
        GovernanceBundleStorePort,
        GovernanceValidationReportStorePort,
        GovernanceSnapshotStorePort,
        GovernanceActivationStorePort,
        GovernanceAuditStorePort {

  private final Map<String, GovernanceArtifact> artifactsById = new ConcurrentHashMap<>();
  private final Map<String, String> artifactKeyToId = new ConcurrentHashMap<>();
  private final Map<String, GovernanceBundle> bundlesById = new ConcurrentHashMap<>();
  private final Map<String, String> bundleKeyToId = new ConcurrentHashMap<>();
  private final Map<String, GovernanceValidationReport> reportsById = new ConcurrentHashMap<>();
  private final Map<String, List<String>> reportsByBundle = new ConcurrentHashMap<>();
  private final Map<String, ActiveGovernanceSnapshot> snapshotsById = new ConcurrentHashMap<>();
  private final Map<String, GovernanceActivation> activationsByScope = new ConcurrentHashMap<>();
  private final List<GovernanceAuditEvent> audit = new ArrayList<>();

  private static String artifactKey(GovernanceArtifactType t, String c, String v) {
    return t.name() + "|" + c + "|" + v;
  }

  private static String bundleKey(String code, String version, String scope) {
    return code + "|" + version + "|" + scope;
  }

  @Override
  public synchronized GovernanceArtifact insert(GovernanceArtifact artifact) {
    String key =
        artifactKey(
            artifact.artifactRef().artifactType(),
            artifact.artifactRef().artifactCode(),
            artifact.artifactRef().artifactVersion());
    if (artifactKeyToId.containsKey(key)) {
      throw new IllegalStateException("ARTIFACT_VERSION_CONFLICT");
    }
    artifactsById.put(artifact.artifactId(), artifact);
    artifactKeyToId.put(key, artifact.artifactId());
    return artifact;
  }

  @Override
  public Optional<GovernanceArtifact> findArtifactById(String artifactId) {
    return Optional.ofNullable(artifactsById.get(artifactId));
  }

  @Override
  public Optional<GovernanceArtifact> findByRef(GovernanceArtifactRef ref) {
    return findByTypeCodeVersion(ref.artifactType(), ref.artifactCode(), ref.artifactVersion());
  }

  @Override
  public Optional<GovernanceArtifact> findByTypeCodeVersion(
      GovernanceArtifactType type, String code, String version) {
    String id = artifactKeyToId.get(artifactKey(type, code, version));
    return id == null ? Optional.empty() : Optional.ofNullable(artifactsById.get(id));
  }

  @Override
  public synchronized GovernanceArtifact update(GovernanceArtifact artifact) {
    GovernanceArtifact current = artifactsById.get(artifact.artifactId());
    if (current == null) {
      throw new IllegalStateException("ARTIFACT_NOT_FOUND");
    }
    if (artifact.optimisticVersion() != current.optimisticVersion() + 1) {
      throw new IllegalStateException("OPTIMISTIC_LOCK");
    }
    artifactsById.put(artifact.artifactId(), artifact);
    return artifact;
  }

  @Override
  public List<GovernanceArtifact> findByIds(List<String> artifactIds) {
    List<GovernanceArtifact> list = new ArrayList<>();
    for (String id : artifactIds) {
      GovernanceArtifact a = artifactsById.get(id);
      if (a != null) {
        list.add(a);
      }
    }
    return List.copyOf(list);
  }

  @Override
  public synchronized GovernanceBundle insert(GovernanceBundle bundle) {
    String key =
        bundleKey(bundle.bundleCode(), bundle.bundleVersion(), bundle.governanceScope().code());
    if (bundleKeyToId.containsKey(key)) {
      throw new IllegalStateException("BUNDLE_VERSION_CONFLICT");
    }
    bundlesById.put(bundle.bundleId(), bundle);
    bundleKeyToId.put(key, bundle.bundleId());
    return bundle;
  }

  @Override
  public Optional<GovernanceBundle> findBundleById(String bundleId) {
    return Optional.ofNullable(bundlesById.get(bundleId));
  }

  @Override
  public Optional<GovernanceBundle> findByCodeVersionScope(
      String bundleCode, String bundleVersion, GovernanceScope scope) {
    String id = bundleKeyToId.get(bundleKey(bundleCode, bundleVersion, scope.code()));
    return id == null ? Optional.empty() : Optional.ofNullable(bundlesById.get(id));
  }

  @Override
  public synchronized GovernanceBundle update(GovernanceBundle bundle) {
    GovernanceBundle current = bundlesById.get(bundle.bundleId());
    if (current == null || bundle.optimisticVersion() != current.optimisticVersion() + 1) {
      throw new IllegalStateException("OPTIMISTIC_LOCK");
    }
    bundlesById.put(bundle.bundleId(), bundle);
    return bundle;
  }

  @Override
  public synchronized GovernanceValidationReport insert(GovernanceValidationReport report) {
    reportsById.put(report.reportId(), report);
    reportsByBundle
        .computeIfAbsent(report.bundleId(), k -> new ArrayList<>())
        .add(report.reportId());
    return report;
  }

  @Override
  public Optional<GovernanceValidationReport> findReportById(String reportId) {
    return Optional.ofNullable(reportsById.get(reportId));
  }

  @Override
  public Optional<GovernanceValidationReport> findLatestByBundleId(String bundleId) {
    List<String> ids = reportsByBundle.getOrDefault(bundleId, List.of());
    if (ids.isEmpty()) {
      return Optional.empty();
    }
    return Optional.ofNullable(reportsById.get(ids.get(ids.size() - 1)));
  }

  @Override
  public synchronized ActiveGovernanceSnapshot insert(ActiveGovernanceSnapshot snapshot) {
    snapshotsById.put(snapshot.snapshotId(), snapshot);
    return snapshot;
  }

  @Override
  public Optional<ActiveGovernanceSnapshot> findSnapshotById(String snapshotId) {
    return Optional.ofNullable(snapshotsById.get(snapshotId));
  }

  @Override
  public Optional<ActiveGovernanceSnapshot> findByBundleRefAndDigest(
      String bundleRef, String digest) {
    return snapshotsById.values().stream()
        .filter(s -> s.bundleRef().equals(bundleRef) && s.bundleDigest().equals(digest))
        .findFirst();
  }

  @Override
  public Optional<GovernanceActivation> findActive(GovernanceScope scope) {
    return Optional.ofNullable(activationsByScope.get(scope.code()));
  }

  @Override
  public synchronized Optional<GovernanceActivation> activate(
      GovernanceActivation activation, long expectedVersion) {
    GovernanceActivation current = activationsByScope.get(activation.scopeCode());
    long currentVersion = current == null ? -1L : current.optimisticVersion();
    if (currentVersion != expectedVersion) {
      return Optional.empty();
    }
    if (current != null
        && current.activeSnapshotId().equals(activation.activeSnapshotId())) {
      return Optional.of(current); // idempotent
    }
    activationsByScope.put(activation.scopeCode(), activation);
    return Optional.of(activation);
  }

  @Override
  public synchronized void append(GovernanceAuditEvent event) {
    audit.add(event);
  }

  @Override
  public synchronized List<GovernanceAuditEvent> findByTargetRef(String targetRef, int limit) {
    return audit.stream()
        .filter(e -> targetRef.equals(e.targetRef()))
        .sorted(Comparator.comparing(GovernanceAuditEvent::occurredAt).reversed())
        .limit(limit)
        .toList();
  }

  public void clear() {
    artifactsById.clear();
    artifactKeyToId.clear();
    bundlesById.clear();
    bundleKeyToId.clear();
    reportsById.clear();
    reportsByBundle.clear();
    snapshotsById.clear();
    activationsByScope.clear();
    audit.clear();
  }
}
