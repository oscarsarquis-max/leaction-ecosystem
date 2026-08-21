package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.GovernanceActivation;
import br.com.banco.spider.governance.GovernanceArtifact;
import br.com.banco.spider.governance.GovernanceArtifactRef;
import br.com.banco.spider.governance.GovernanceArtifactType;
import br.com.banco.spider.governance.GovernanceAuditEvent;
import br.com.banco.spider.governance.GovernanceBundle;
import br.com.banco.spider.governance.GovernanceLifecycleState;
import br.com.banco.spider.governance.GovernanceScope;
import br.com.banco.spider.governance.GovernanceSnapshotCodec;
import br.com.banco.spider.governance.GovernanceValidationFinding;
import br.com.banco.spider.governance.GovernanceValidationReport;
import br.com.banco.spider.governance.port.GovernanceActivationStorePort;
import br.com.banco.spider.governance.port.GovernanceArtifactStorePort;
import br.com.banco.spider.governance.port.GovernanceAuditStorePort;
import br.com.banco.spider.governance.port.GovernanceBundleStorePort;
import br.com.banco.spider.governance.port.GovernanceSnapshotStorePort;
import br.com.banco.spider.governance.port.GovernanceValidationReportStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceActivationEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceActivationHistoryEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceArtifactEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceAuditEventEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceBundleArtifactEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceBundleEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceSnapshotEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceValidationReportEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.GovernanceActivationHistoryJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.GovernanceActivationJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.GovernanceArtifactJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.GovernanceAuditEventJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.GovernanceBundleArtifactJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.GovernanceBundleJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.GovernanceSnapshotJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.GovernanceValidationReportJpaRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Primary;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/** Adapters JPA reais para todas as Governance Store Ports. */
@Component
@Primary
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaGovernanceStoresAdapter
    implements GovernanceArtifactStorePort,
        GovernanceBundleStorePort,
        GovernanceValidationReportStorePort,
        GovernanceSnapshotStorePort,
        GovernanceActivationStorePort,
        GovernanceAuditStorePort {

  private final GovernanceArtifactJpaRepository artifacts;
  private final GovernanceBundleJpaRepository bundles;
  private final GovernanceBundleArtifactJpaRepository bundleArtifacts;
  private final GovernanceValidationReportJpaRepository reports;
  private final GovernanceSnapshotJpaRepository snapshots;
  private final GovernanceActivationJpaRepository activations;
  private final GovernanceActivationHistoryJpaRepository activationHistory;
  private final GovernanceAuditEventJpaRepository auditEvents;
  private final GovernanceSnapshotCodec snapshotCodec;
  private final ObjectMapper findingsMapper = new ObjectMapper().findAndRegisterModules();

  public JpaGovernanceStoresAdapter(
      GovernanceArtifactJpaRepository artifacts,
      GovernanceBundleJpaRepository bundles,
      GovernanceBundleArtifactJpaRepository bundleArtifacts,
      GovernanceValidationReportJpaRepository reports,
      GovernanceSnapshotJpaRepository snapshots,
      GovernanceActivationJpaRepository activations,
      GovernanceActivationHistoryJpaRepository activationHistory,
      GovernanceAuditEventJpaRepository auditEvents,
      GovernanceSnapshotCodec snapshotCodec) {
    this.artifacts = artifacts;
    this.bundles = bundles;
    this.bundleArtifacts = bundleArtifacts;
    this.reports = reports;
    this.snapshots = snapshots;
    this.activations = activations;
    this.activationHistory = activationHistory;
    this.auditEvents = auditEvents;
    this.snapshotCodec = snapshotCodec;
  }

  @Override
  @Transactional
  public GovernanceArtifact insert(GovernanceArtifact artifact) {
    if (artifacts
        .findByArtifactTypeAndArtifactCodeAndArtifactVersion(
            artifact.artifactRef().artifactType(),
            artifact.artifactRef().artifactCode(),
            artifact.artifactRef().artifactVersion())
        .isPresent()) {
      throw new IllegalStateException("ARTIFACT_VERSION_CONFLICT");
    }
    return toArtifact(artifacts.save(toEntity(artifact)));
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<GovernanceArtifact> findArtifactById(String artifactId) {
    return artifacts.findById(artifactId).map(JpaGovernanceStoresAdapter::toArtifact);
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<GovernanceArtifact> findByRef(GovernanceArtifactRef ref) {
    return findByTypeCodeVersion(ref.artifactType(), ref.artifactCode(), ref.artifactVersion());
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<GovernanceArtifact> findByTypeCodeVersion(
      GovernanceArtifactType type, String code, String version) {
    return artifacts
        .findByArtifactTypeAndArtifactCodeAndArtifactVersion(type, code, version)
        .map(JpaGovernanceStoresAdapter::toArtifact);
  }

  @Override
  @Transactional
  public GovernanceArtifact update(GovernanceArtifact artifact) {
    GovernanceArtifactEntity e =
        artifacts
            .findById(artifact.artifactId())
            .orElseThrow(() -> new IllegalStateException("ARTIFACT_NOT_FOUND"));
    if (e.getVersion() != artifact.optimisticVersion() - 1) {
      throw new IllegalStateException("OPTIMISTIC_LOCK");
    }
    applyArtifact(e, artifact);
    return toArtifact(artifacts.save(e));
  }

  @Override
  @Transactional(readOnly = true)
  public List<GovernanceArtifact> findByIds(List<String> artifactIds) {
    List<GovernanceArtifact> out = new ArrayList<>();
    for (String id : artifactIds) {
      artifacts.findById(id).map(JpaGovernanceStoresAdapter::toArtifact).ifPresent(out::add);
    }
    return List.copyOf(out);
  }

  @Override
  @Transactional
  public GovernanceBundle insert(GovernanceBundle bundle) {
    if (bundles
        .findByBundleCodeAndBundleVersionAndGovernanceScope(
            bundle.bundleCode(), bundle.bundleVersion(), bundle.governanceScope().code())
        .isPresent()) {
      throw new IllegalStateException("BUNDLE_VERSION_CONFLICT");
    }
    bundles.save(toEntity(bundle));
    int i = 0;
    for (GovernanceArtifactRef ref : bundle.artifactRefs()) {
      GovernanceBundleArtifactEntity ba = new GovernanceBundleArtifactEntity();
      ba.setBundleId(bundle.bundleId());
      ba.setArtifactType(ref.artifactType());
      ba.setArtifactCode(ref.artifactCode());
      ba.setArtifactVersion(ref.artifactVersion());
      ba.setOrdinalPos(i++);
      bundleArtifacts.save(ba);
    }
    return bundle;
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<GovernanceBundle> findBundleById(String bundleId) {
    return bundles.findById(bundleId).map(this::toBundle);
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<GovernanceBundle> findByCodeVersionScope(
      String bundleCode, String bundleVersion, GovernanceScope scope) {
    return bundles
        .findByBundleCodeAndBundleVersionAndGovernanceScope(
            bundleCode, bundleVersion, scope.code())
        .map(this::toBundle);
  }

  @Override
  @Transactional
  public GovernanceBundle update(GovernanceBundle bundle) {
    GovernanceBundleEntity e =
        bundles
            .findById(bundle.bundleId())
            .orElseThrow(() -> new IllegalStateException("BUNDLE_NOT_FOUND"));
    if (e.getVersion() != bundle.optimisticVersion() - 1) {
      throw new IllegalStateException("OPTIMISTIC_LOCK");
    }
    applyBundle(e, bundle);
    bundles.save(e);
    return bundle;
  }

  @Override
  @Transactional
  public GovernanceValidationReport insert(GovernanceValidationReport report) {
    GovernanceValidationReportEntity e = new GovernanceValidationReportEntity();
    e.setReportId(report.reportId());
    e.setBundleId(report.bundleId());
    e.setValidatorVersion(report.validatorVersion());
    e.setPassed(report.passed());
    e.setErrorCount(report.errorCount());
    e.setWarningCount(report.warningCount());
    e.setInfoCount(report.infoCount());
    try {
      e.setFindingsJson(findingsMapper.writeValueAsString(report.findings()));
    } catch (Exception ex) {
      throw new IllegalStateException("FINDINGS_ENCODE_FAILED");
    }
    e.setCreatedAt(report.createdAt());
    e.setCreatedByPrincipal(report.createdByPrincipalRef());
    reports.save(e);
    return report;
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<GovernanceValidationReport> findReportById(String reportId) {
    return reports.findById(reportId).map(this::toReport);
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<GovernanceValidationReport> findLatestByBundleId(String bundleId) {
    return reports.findFirstByBundleIdOrderByCreatedAtDesc(bundleId).map(this::toReport);
  }

  @Override
  @Transactional
  public ActiveGovernanceSnapshot insert(ActiveGovernanceSnapshot snapshot) {
    GovernanceSnapshotEntity e = new GovernanceSnapshotEntity();
    e.setSnapshotId(snapshot.snapshotId());
    e.setBundleRef(snapshot.bundleRef());
    e.setBundleDigest(snapshot.bundleDigest());
    e.setGovernanceScope(snapshot.governanceScope().code());
    e.setSnapshotDigest(snapshot.snapshotDigest());
    e.setCompiledAt(snapshot.compiledAt());
    e.setSnapshotJson(snapshotCodec.encode(snapshot));
    snapshots.save(e);
    return snapshot;
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<ActiveGovernanceSnapshot> findSnapshotById(String snapshotId) {
    return snapshots.findById(snapshotId).map(this::toSnapshot);
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<ActiveGovernanceSnapshot> findByBundleRefAndDigest(
      String bundleRef, String digest) {
    return snapshots.findByBundleRefAndBundleDigest(bundleRef, digest).map(this::toSnapshot);
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<GovernanceActivation> findActive(GovernanceScope scope) {
    return activations.findById(scope.code()).map(JpaGovernanceStoresAdapter::toActivation);
  }

  @Override
  @Transactional
  public Optional<GovernanceActivation> activate(
      GovernanceActivation activation, long expectedVersion) {
    Optional<GovernanceActivationEntity> currentOpt =
        activations.findById(activation.scopeCode());
    long currentVersion = currentOpt.map(GovernanceActivationEntity::getVersion).orElse(-1L);
    if (currentVersion != expectedVersion) {
      return Optional.empty();
    }
    if (currentOpt.isPresent()
        && currentOpt.get().getActiveSnapshotId().equals(activation.activeSnapshotId())) {
      return Optional.of(toActivation(currentOpt.get()));
    }
    GovernanceActivationEntity e = currentOpt.orElseGet(GovernanceActivationEntity::new);
    e.setGovernanceScope(activation.scopeCode());
    e.setActiveSnapshotId(activation.activeSnapshotId());
    e.setPreviousSnapshotId(activation.previousSnapshotId());
    e.setActivationSequence(activation.activationSequence());
    e.setActivatedAt(activation.activatedAt());
    e.setActivatedByPrincipal(activation.activatedByPrincipalRef());
    e.setReasonCode(activation.reasonCode());
    if (currentOpt.isEmpty()) {
      e.setVersion(0L);
    }
    GovernanceActivationEntity saved = activations.save(e);
    GovernanceActivationHistoryEntity h = new GovernanceActivationHistoryEntity();
    h.setGovernanceScope(activation.scopeCode());
    h.setActivationSequence(activation.activationSequence());
    h.setActiveSnapshotId(activation.activeSnapshotId());
    h.setPreviousSnapshotId(activation.previousSnapshotId());
    h.setActivatedAt(activation.activatedAt());
    h.setActivatedByPrincipal(activation.activatedByPrincipalRef());
    h.setReasonCode(activation.reasonCode());
    activationHistory.save(h);
    return Optional.of(toActivation(saved));
  }

  @Override
  @Transactional
  public void append(GovernanceAuditEvent event) {
    GovernanceAuditEventEntity e = new GovernanceAuditEventEntity();
    e.setEventId(event.eventId());
    e.setCommandType(event.commandType());
    e.setTargetType(event.targetType());
    e.setTargetRef(event.targetRef());
    e.setActorPrincipalRef(event.actorPrincipalRef());
    e.setOutcome(event.outcome());
    e.setReasonCode(event.reasonCode());
    e.setPreviousLifecycleState(event.previousLifecycleState());
    e.setNewLifecycleState(event.newLifecycleState());
    e.setOccurredAt(event.occurredAt());
    e.setCorrelationId(event.correlationId());
    auditEvents.save(e);
  }

  @Override
  @Transactional(readOnly = true)
  public List<GovernanceAuditEvent> findByTargetRef(String targetRef, int limit) {
    return auditEvents
        .findByTargetRefOrderByOccurredAtDesc(targetRef, PageRequest.of(0, Math.max(1, limit)))
        .stream()
        .map(JpaGovernanceStoresAdapter::toAudit)
        .toList();
  }

  private ActiveGovernanceSnapshot toSnapshot(GovernanceSnapshotEntity e) {
    if (e.getSnapshotJson() == null || e.getSnapshotJson().isBlank()) {
      throw new IllegalStateException("SNAPSHOT_JSON_MISSING");
    }
    return snapshotCodec.decode(e.getSnapshotJson());
  }

  private GovernanceBundle toBundle(GovernanceBundleEntity e) {
    List<GovernanceArtifactRef> refs =
        bundleArtifacts.findByBundleIdOrderByOrdinalPosAsc(e.getBundleId()).stream()
            .map(
                ba ->
                    new GovernanceArtifactRef(
                        ba.getArtifactType(), ba.getArtifactCode(), ba.getArtifactVersion()))
            .toList();
    return new GovernanceBundle(
        e.getBundleId(),
        e.getBundleCode(),
        e.getBundleVersion(),
        new GovernanceScope(e.getGovernanceScope()),
        refs,
        e.getBundleDigest(),
        e.getLifecycleState(),
        e.getValidationReportRef(),
        e.getCreatedByPrincipal(),
        e.getCreatedAt(),
        e.getValidatedAt(),
        e.getPublishedAt(),
        e.getDeprecatedAt(),
        e.getRetiredAt(),
        e.getRevokedAt(),
        e.getReasonCode(),
        e.getVersion());
  }

  private GovernanceValidationReport toReport(GovernanceValidationReportEntity e) {
    List<GovernanceValidationFinding> findings = List.of();
    if (e.getFindingsJson() != null && !e.getFindingsJson().isBlank()) {
      try {
        findings =
            findingsMapper.readValue(
                e.getFindingsJson(), new TypeReference<List<GovernanceValidationFinding>>() {});
      } catch (Exception ex) {
        throw new IllegalStateException("FINDINGS_DECODE_FAILED");
      }
    }
    return new GovernanceValidationReport(
        e.getReportId(),
        e.getBundleId(),
        e.getValidatorVersion(),
        e.isPassed(),
        e.getErrorCount(),
        e.getWarningCount(),
        e.getInfoCount(),
        findings,
        e.getCreatedAt(),
        e.getCreatedByPrincipal());
  }

  private static GovernanceArtifact toArtifact(GovernanceArtifactEntity e) {
    return new GovernanceArtifact(
        e.getArtifactId(),
        new GovernanceArtifactRef(e.getArtifactType(), e.getArtifactCode(), e.getArtifactVersion()),
        e.getSchemaVersion(),
        e.getCanonicalContent(),
        e.getContentDigest(),
        e.getLifecycleState(),
        e.getCreatedByPrincipal(),
        e.getCreatedAt(),
        e.getValidatedAt(),
        e.getPublishedAt(),
        e.getDeprecatedAt(),
        e.getRetiredAt(),
        e.getRevokedAt(),
        e.getLifecycleReasonCode(),
        e.getVersion());
  }

  private static GovernanceArtifactEntity toEntity(GovernanceArtifact a) {
    GovernanceArtifactEntity e = new GovernanceArtifactEntity();
    applyArtifact(e, a);
    return e;
  }

  private static void applyArtifact(GovernanceArtifactEntity e, GovernanceArtifact a) {
    e.setArtifactId(a.artifactId());
    e.setArtifactType(a.artifactRef().artifactType());
    e.setArtifactCode(a.artifactRef().artifactCode());
    e.setArtifactVersion(a.artifactRef().artifactVersion());
    e.setSchemaVersion(a.schemaVersion());
    e.setCanonicalContent(a.canonicalContent());
    e.setContentDigest(a.contentDigest());
    e.setLifecycleState(a.lifecycleState());
    e.setCreatedByPrincipal(a.createdByPrincipalRef());
    e.setCreatedAt(a.createdAt());
    e.setValidatedAt(a.validatedAt());
    e.setPublishedAt(a.publishedAt());
    e.setDeprecatedAt(a.deprecatedAt());
    e.setRetiredAt(a.retiredAt());
    e.setRevokedAt(a.revokedAt());
    e.setLifecycleReasonCode(a.lifecycleReasonCode());
  }

  private static GovernanceBundleEntity toEntity(GovernanceBundle b) {
    GovernanceBundleEntity e = new GovernanceBundleEntity();
    applyBundle(e, b);
    return e;
  }

  private static void applyBundle(GovernanceBundleEntity e, GovernanceBundle b) {
    e.setBundleId(b.bundleId());
    e.setBundleCode(b.bundleCode());
    e.setBundleVersion(b.bundleVersion());
    e.setGovernanceScope(b.governanceScope().code());
    e.setBundleDigest(b.bundleDigest());
    e.setLifecycleState(b.lifecycleState());
    e.setValidationReportRef(b.validationReportRef());
    e.setCreatedByPrincipal(b.createdByPrincipalRef());
    e.setCreatedAt(b.createdAt());
    e.setValidatedAt(b.validatedAt());
    e.setPublishedAt(b.publishedAt());
    e.setDeprecatedAt(b.deprecatedAt());
    e.setRetiredAt(b.retiredAt());
    e.setRevokedAt(b.revokedAt());
    e.setReasonCode(b.reasonCode());
  }

  private static GovernanceActivation toActivation(GovernanceActivationEntity e) {
    return new GovernanceActivation(
        e.getGovernanceScope(),
        e.getActiveSnapshotId(),
        e.getPreviousSnapshotId(),
        e.getActivationSequence(),
        e.getActivatedAt(),
        e.getActivatedByPrincipal(),
        e.getReasonCode(),
        e.getVersion());
  }

  private static GovernanceAuditEvent toAudit(GovernanceAuditEventEntity e) {
    return new GovernanceAuditEvent(
        e.getEventId(),
        e.getCommandType(),
        e.getTargetType(),
        e.getTargetRef(),
        e.getActorPrincipalRef(),
        e.getOutcome(),
        e.getReasonCode(),
        e.getPreviousLifecycleState(),
        e.getNewLifecycleState(),
        e.getOccurredAt(),
        e.getCorrelationId());
  }
}
