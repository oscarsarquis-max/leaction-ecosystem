package br.com.banco.spider.governance;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.governance.port.ActiveGovernanceSnapshotProviderPort;
import br.com.banco.spider.governance.port.GovernanceActivationStorePort;
import br.com.banco.spider.governance.port.GovernanceArtifactStorePort;
import br.com.banco.spider.governance.port.GovernanceAuditStorePort;
import br.com.banco.spider.governance.port.GovernanceBundleStorePort;
import br.com.banco.spider.governance.port.GovernanceSnapshotStorePort;
import br.com.banco.spider.governance.port.GovernanceValidationReportStorePort;
import java.time.Instant;
import java.util.List;
import java.util.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/** Comandos do Control Plane — deny-by-default via GovernanceAuthorizationPort. */
@Service
public class GovernanceControlPlaneService {

  private static final Logger log = LoggerFactory.getLogger(GovernanceControlPlaneService.class);

  private final GovernanceAuthorizationPort authorization;
  private final GovernanceArtifactStorePort artifactStore;
  private final GovernanceBundleStorePort bundleStore;
  private final GovernanceValidationReportStorePort reportStore;
  private final GovernanceSnapshotStorePort snapshotStore;
  private final GovernanceActivationStorePort activationStore;
  private final GovernanceAuditStorePort auditStore;
  private final GovernanceArtifactCodecRegistry codecs;
  private final GovernanceArtifactDigestService digestService;
  private final GovernanceValidationService validationService;
  private final GovernanceSnapshotCompiler compiler;
  private final ActiveGovernanceSnapshotProviderPort snapshotProvider;
  private final GovernanceApprovalPolicy approvalPolicy;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final int maxArtifactBytes;

  public GovernanceControlPlaneService(
      GovernanceAuthorizationPort authorization,
      GovernanceArtifactStorePort artifactStore,
      GovernanceBundleStorePort bundleStore,
      GovernanceValidationReportStorePort reportStore,
      GovernanceSnapshotStorePort snapshotStore,
      GovernanceActivationStorePort activationStore,
      GovernanceAuditStorePort auditStore,
      GovernanceArtifactCodecRegistry codecs,
      GovernanceArtifactDigestService digestService,
      GovernanceValidationService validationService,
      GovernanceSnapshotCompiler compiler,
      ActiveGovernanceSnapshotProviderPort snapshotProvider,
      GovernanceApprovalPolicy approvalPolicy,
      IdentifierGenerator ids,
      SpiderClock clock,
      @org.springframework.beans.factory.annotation.Value(
              "${spider.governance.max-artifact-bytes:262144}")
          int maxArtifactBytes) {
    this.authorization = authorization;
    this.artifactStore = artifactStore;
    this.bundleStore = bundleStore;
    this.reportStore = reportStore;
    this.snapshotStore = snapshotStore;
    this.activationStore = activationStore;
    this.auditStore = auditStore;
    this.codecs = codecs;
    this.digestService = digestService;
    this.validationService = validationService;
    this.compiler = compiler;
    this.snapshotProvider = snapshotProvider;
    this.approvalPolicy = approvalPolicy;
    this.ids = ids;
    this.clock = clock;
    this.maxArtifactBytes = maxArtifactBytes;
  }

  public Mono<GovernanceArtifact> registerArtifactUnsupported() {
    return Mono.error(new UnsupportedOperationException("use registerTyped"));
  }

  public GovernanceArtifact registerTyped(
      String actor,
      GovernanceArtifactType type,
      String code,
      String version,
      String schemaVersion,
      String canonicalContent) {
    requireAuthSync("governance.artifact.register", actor);
    if (canonicalContent.length() > maxArtifactBytes) {
      throw new IllegalArgumentException("ARTIFACT_TOO_LARGE");
    }
    Instant now = clock.now();
    String digest =
        digestService.digestArtifact(type, code, version, schemaVersion, canonicalContent);
    GovernanceArtifact artifact =
        new GovernanceArtifact(
            ids.nextId("gart"),
            new GovernanceArtifactRef(type, code, version),
            schemaVersion,
            canonicalContent,
            digest,
            GovernanceLifecycleState.DRAFT,
            actor,
            now,
            null,
            null,
            null,
            null,
            null,
            null,
            0L);
    GovernanceArtifact stored = artifactStore.insert(artifact);
    audit(actor, "REGISTER_ARTIFACT", type.name(), stored.artifactRef().toString(), "OK", null, "DRAFT");
    log.info("event=artifact_registered type={} reasonCode=OK", type);
    return stored;
  }

  public GovernanceArtifact validateArtifact(String actor, String artifactId) {
    requireAuthSync("governance.artifact.validate", actor);
    GovernanceArtifact current =
        artifactStore.findArtifactById(artifactId).orElseThrow(() -> new IllegalStateException("NOT_FOUND"));
    if (current.lifecycleState() != GovernanceLifecycleState.DRAFT) {
      throw new IllegalStateException("INVALID_LIFECYCLE");
    }
    String expected =
        digestService.digestArtifact(
            current.artifactRef().artifactType(),
            current.artifactRef().artifactCode(),
            current.artifactRef().artifactVersion(),
            current.schemaVersion(),
            current.canonicalContent());
    if (!digestService.secureEquals(expected, current.contentDigest())) {
      throw new IllegalStateException("ARTIFACT_DIGEST_MISMATCH");
    }
    codecs.decode(
        current.artifactRef().artifactType(),
        current.canonicalContent(),
        codecs.domainClass(current.artifactRef().artifactType()));
    GovernanceArtifact updated =
        new GovernanceArtifact(
            current.artifactId(),
            current.artifactRef(),
            current.schemaVersion(),
            current.canonicalContent(),
            current.contentDigest(),
            GovernanceLifecycleState.VALIDATED,
            current.createdByPrincipalRef(),
            current.createdAt(),
            clock.now(),
            null,
            null,
            null,
            null,
            null,
            current.optimisticVersion() + 1);
    artifactStore.update(updated);
    audit(
        actor,
        "VALIDATE_ARTIFACT",
        "ARTIFACT",
        updated.artifactRef().toString(),
        "OK",
        "DRAFT",
        "VALIDATED");
    log.info(
        "event=artifact_validated type={} reasonCode=OK",
        updated.artifactRef().artifactType());
    return updated;
  }

  public GovernanceArtifact publishArtifact(String actor, String artifactId) {
    requireAuthSync("governance.artifact.publish", actor);
    GovernanceArtifact current =
        artifactStore.findArtifactById(artifactId).orElseThrow(() -> new IllegalStateException("NOT_FOUND"));
    if (current.lifecycleState() == GovernanceLifecycleState.PUBLISHED) {
      return current; // idempotent
    }
    if (current.lifecycleState() != GovernanceLifecycleState.VALIDATED) {
      throw new IllegalStateException("INVALID_LIFECYCLE");
    }
    if (approvalPolicy.requireDistinctPublisher()
        && Objects.equals(actor, current.createdByPrincipalRef())) {
      throw new IllegalStateException("APPROVAL_POLICY_DISTINCT_PUBLISHER");
    }
    String expected =
        digestService.digestArtifact(
            current.artifactRef().artifactType(),
            current.artifactRef().artifactCode(),
            current.artifactRef().artifactVersion(),
            current.schemaVersion(),
            current.canonicalContent());
    if (!digestService.secureEquals(expected, current.contentDigest())) {
      throw new IllegalStateException("ARTIFACT_DIGEST_MISMATCH");
    }
    GovernanceArtifact published =
        new GovernanceArtifact(
            current.artifactId(),
            current.artifactRef(),
            current.schemaVersion(),
            current.canonicalContent(),
            current.contentDigest(),
            GovernanceLifecycleState.PUBLISHED,
            current.createdByPrincipalRef(),
            current.createdAt(),
            current.validatedAt(),
            clock.now(),
            null,
            null,
            null,
            null,
            current.optimisticVersion() + 1);
    artifactStore.update(published);
    audit(
        actor,
        "PUBLISH_ARTIFACT",
        "ARTIFACT",
        published.artifactRef().toString(),
        "OK",
        "VALIDATED",
        "PUBLISHED");
    log.info(
        "event=artifact_published type={} reasonCode=OK",
        published.artifactRef().artifactType());
    return published;
  }

  public GovernanceBundle createBundle(
      String actor,
      String bundleCode,
      String bundleVersion,
      GovernanceScope scope,
      List<GovernanceArtifactRef> refs) {
    requireAuthSync("governance.bundle.create", actor);
    if (refs.size() > 500) {
      throw new IllegalArgumentException("TOO_MANY_ARTIFACTS");
    }
    GovernanceBundle draft =
        new GovernanceBundle(
            ids.nextId("gbdl"),
            bundleCode,
            bundleVersion,
            scope,
            refs,
            "pending",
            GovernanceLifecycleState.DRAFT,
            null,
            actor,
            clock.now(),
            null,
            null,
            null,
            null,
            null,
            null,
            0L);
    String digest;
    try {
      digest = compiler.computeBundleDigest(draft);
    } catch (IllegalStateException ex) {
      digest = "pending-incomplete";
    }
    GovernanceBundle withDigest =
        new GovernanceBundle(
            draft.bundleId(),
            draft.bundleCode(),
            draft.bundleVersion(),
            draft.governanceScope(),
            draft.artifactRefs(),
            digest,
            draft.lifecycleState(),
            null,
            draft.createdByPrincipalRef(),
            draft.createdAt(),
            null,
            null,
            null,
            null,
            null,
            null,
            0L);
    GovernanceBundle stored = bundleStore.insert(withDigest);
    audit(actor, "CREATE_BUNDLE", "BUNDLE", stored.exactRef(), "OK", null, "DRAFT");
    log.info("event=bundle_created reasonCode=OK");
    return stored;
  }

  public GovernanceValidationReport validateBundle(String actor, String bundleId) {
    requireAuthSync("governance.bundle.validate", actor);
    GovernanceBundle bundle =
        bundleStore.findBundleById(bundleId).orElseThrow(() -> new IllegalStateException("NOT_FOUND"));
    GovernanceValidationReport report = validationService.validateBundle(bundle, actor);
    reportStore.insert(report);
    GovernanceBundle updated =
        new GovernanceBundle(
            bundle.bundleId(),
            bundle.bundleCode(),
            bundle.bundleVersion(),
            bundle.governanceScope(),
            bundle.artifactRefs(),
            bundle.bundleDigest(),
            report.passed() ? GovernanceLifecycleState.VALIDATED : bundle.lifecycleState(),
            report.reportId(),
            bundle.createdByPrincipalRef(),
            bundle.createdAt(),
            report.passed() ? clock.now() : bundle.validatedAt(),
            bundle.publishedAt(),
            bundle.deprecatedAt(),
            bundle.retiredAt(),
            bundle.revokedAt(),
            bundle.reasonCode(),
            bundle.optimisticVersion() + 1);
    if (report.passed()) {
      bundleStore.update(updated);
      log.info("event=bundle_validation_passed reasonCode=OK");
    } else {
      log.info("event=bundle_validation_failed errors={}", report.errorCount());
    }
    audit(
        actor,
        "VALIDATE_BUNDLE",
        "BUNDLE",
        bundle.exactRef(),
        report.passed() ? "OK" : "FAILED",
        bundle.lifecycleState().name(),
        updated.lifecycleState().name());
    return report;
  }

  public ActiveGovernanceSnapshot publishBundle(String actor, String bundleId) {
    requireAuthSync("governance.bundle.publish", actor);
    GovernanceBundle bundle =
        bundleStore.findBundleById(bundleId).orElseThrow(() -> new IllegalStateException("NOT_FOUND"));
    if (approvalPolicy.requireDistinctPublisher()
        && Objects.equals(actor, bundle.createdByPrincipalRef())) {
      throw new IllegalStateException("APPROVAL_POLICY_DISTINCT_PUBLISHER");
    }
    GovernanceValidationReport latest =
        reportStore
            .findLatestByBundleId(bundleId)
            .orElseThrow(() -> new IllegalStateException("NO_VALIDATION_REPORT"));
    if (!latest.passed() || latest.errorCount() > 0) {
      throw new IllegalStateException("VALIDATION_ERRORS");
    }
    // TOCTOU revalidate
    GovernanceValidationReport recheck = validationService.validateBundle(bundle, actor);
    if (!recheck.passed()) {
      reportStore.insert(recheck);
      throw new IllegalStateException("TOCTOU_VALIDATION_FAILED");
    }
    String recomputed = compiler.computeBundleDigest(bundle);
    if (!digestService.secureEquals(recomputed, bundle.bundleDigest())) {
      throw new IllegalStateException("BUNDLE_DIGEST_MISMATCH");
    }
    // idempotent publish
    if (bundle.isPublished()) {
      return snapshotStore
          .findByBundleRefAndDigest(bundle.exactRef(), bundle.bundleDigest())
          .orElseThrow(() -> new IllegalStateException("SNAPSHOT_MISSING"));
    }
    ActiveGovernanceSnapshot snapshot = compiler.compile(bundle);
    snapshotStore.insert(snapshot);
    GovernanceBundle published =
        new GovernanceBundle(
            bundle.bundleId(),
            bundle.bundleCode(),
            bundle.bundleVersion(),
            bundle.governanceScope(),
            bundle.artifactRefs(),
            bundle.bundleDigest(),
            GovernanceLifecycleState.PUBLISHED,
            recheck.reportId(),
            bundle.createdByPrincipalRef(),
            bundle.createdAt(),
            bundle.validatedAt(),
            clock.now(),
            null,
            null,
            null,
            null,
            bundle.optimisticVersion() + 1);
    bundleStore.update(published);
    audit(actor, "PUBLISH_BUNDLE", "BUNDLE", bundle.exactRef(), "OK", "VALIDATED", "PUBLISHED");
    log.info("event=bundle_published reasonCode=OK");
    return snapshot;
  }

  public GovernanceActivation activateSnapshot(
      String actor, GovernanceScope scope, String snapshotId, String reasonCode) {
    requireAuthSync("governance.snapshot.activate", actor);
    ActiveGovernanceSnapshot snapshot =
        snapshotStore
            .findSnapshotById(snapshotId)
            .orElseThrow(() -> new IllegalStateException("SNAPSHOT_NOT_FOUND"));
    GovernanceActivation current = activationStore.findActive(scope).orElse(null);
    long expected = current == null ? -1L : current.optimisticVersion();
    GovernanceActivation next =
        new GovernanceActivation(
            scope.code(),
            snapshotId,
            current == null ? null : current.activeSnapshotId(),
            current == null ? 1L : current.activationSequence() + 1,
            clock.now(),
            actor,
            reasonCode,
            expected + 1);
    GovernanceActivation won =
        activationStore
            .activate(next, expected)
            .orElseThrow(() -> new IllegalStateException("ACTIVATION_CONFLICT"));
    snapshotProvider.putAfterCommit(scope, snapshot);
    audit(actor, "ACTIVATE_SNAPSHOT", "SNAPSHOT", snapshotId, "OK", null, null);
    log.info("event=activation_succeeded reasonCode=OK");
    return won;
  }

  public GovernanceActivation reactivatePrevious(String actor, GovernanceScope scope, String reason) {
    requireAuthSync("governance.snapshot.reactivate", actor);
    GovernanceActivation current =
        activationStore
            .findActive(scope)
            .orElseThrow(() -> new IllegalStateException("NO_ACTIVE"));
    if (current.previousSnapshotId() == null) {
      throw new IllegalStateException("NO_PREVIOUS");
    }
    return activateSnapshot(actor, scope, current.previousSnapshotId(), reason);
  }

  private Mono<Boolean> authorize(String op, String actor) {
    if (actor == null || actor.isBlank()) {
      return Mono.error(new IllegalStateException("PRINCIPAL_REQUIRED"));
    }
    return authorization
        .authorize(op, actor)
        .flatMap(
            d -> {
              if (d != AuthorizationDecision.PERMIT) {
                log.info("event=unauthorized_command operation={} reasonCode=DENIED", op);
                audit(actor, op, "GOVERNANCE", "-", "DENIED", null, null);
                return Mono.error(new SecurityException("DENIED"));
              }
              return Mono.just(true);
            });
  }

  private void requireAuthSync(String op, String actor) {
    authorize(op, actor).block();
  }

  private void audit(
      String actor,
      String command,
      String targetType,
      String targetRef,
      String outcome,
      String prev,
      String next) {
    auditStore.append(
        new GovernanceAuditEvent(
            ids.nextId("gaud"),
            command,
            targetType,
            targetRef,
            actor,
            outcome,
            outcome,
            prev,
            next,
            clock.now(),
            null));
  }
}
