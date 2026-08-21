package br.com.banco.spider.governance;

import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.route.RouteStatus;
import br.com.banco.spider.governance.port.GovernanceArtifactStorePort;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class GovernanceValidationService {

  public static final String VALIDATOR_VERSION = "gov-validator-1.0";

  private final GovernanceArtifactStorePort artifactStore;
  private final GovernanceArtifactDigestService digestService;
  private final GovernanceArtifactCodecRegistry codecs;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;

  public GovernanceValidationService(
      GovernanceArtifactStorePort artifactStore,
      GovernanceArtifactDigestService digestService,
      GovernanceArtifactCodecRegistry codecs,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this.artifactStore = artifactStore;
    this.digestService = digestService;
    this.codecs = codecs;
    this.ids = ids;
    this.clock = clock;
  }

  public GovernanceValidationReport validateBundle(
      GovernanceBundle bundle, String actorPrincipalRef) {
    List<GovernanceValidationFinding> findings = new ArrayList<>();
    int routes = 0;
    for (GovernanceArtifactRef ref : bundle.artifactRefs()) {
      GovernanceArtifact artifact = artifactStore.findByRef(ref).orElse(null);
      if (artifact == null) {
        findings.add(
            finding(
                GovernanceValidationCategory.REFERENTIAL,
                GovernanceValidationSeverity.ERROR,
                "MISSING_ARTIFACT_REF",
                "Artifact not found",
                ref.toString()));
        continue;
      }
      if (!artifact.isEligibleForNewBundle()) {
        findings.add(
            finding(
                GovernanceValidationCategory.REFERENTIAL,
                GovernanceValidationSeverity.ERROR,
                "ARTIFACT_NOT_ELIGIBLE",
                "Lifecycle not eligible for bundle",
                ref.toString()));
      }
      if (artifact.isRevoked()) {
        findings.add(
            finding(
                GovernanceValidationCategory.SECURITY,
                GovernanceValidationSeverity.ERROR,
                "ARTIFACT_REVOKED",
                "Revoked artifact",
                ref.toString()));
      }
      String expected =
          digestService.digestArtifact(
              ref.artifactType(),
              ref.artifactCode(),
              ref.artifactVersion(),
              artifact.schemaVersion(),
              artifact.canonicalContent());
      if (!digestService.secureEquals(expected, artifact.contentDigest())) {
        findings.add(
            finding(
                GovernanceValidationCategory.STRUCTURAL,
                GovernanceValidationSeverity.ERROR,
                "ARTIFACT_DIGEST_MISMATCH",
                "Digest mismatch",
                ref.toString()));
      }
      try {
        Object domain =
            codecs.decode(
                ref.artifactType(),
                artifact.canonicalContent(),
                codecs.domainClass(ref.artifactType()));
        if (ref.artifactType() == GovernanceArtifactType.ROUTE_DEFINITION) {
          RouteDefinition route = (RouteDefinition) domain;
          routes++;
          if (route.status() != RouteStatus.PUBLISHED) {
            findings.add(
                finding(
                    GovernanceValidationCategory.OPERABILITY,
                    GovernanceValidationSeverity.ERROR,
                    "ROUTE_NOT_PUBLISHED",
                    "Route must be published",
                    ref.toString()));
          }
          if (route.steps() == null || route.steps().isEmpty()) {
            findings.add(
                finding(
                    GovernanceValidationCategory.STRUCTURAL,
                    GovernanceValidationSeverity.ERROR,
                    "ROUTE_NO_STEPS",
                    "Route requires steps",
                    ref.toString()));
          }
        }
        if (ref.artifactType() == GovernanceArtifactType.ADAPTER_BINDING_DESCRIPTOR
            || ref.artifactType() == GovernanceArtifactType.CALLBACK_BINDING_DESCRIPTOR
            || ref.artifactType() == GovernanceArtifactType.STATUS_QUERY_BINDING_DESCRIPTOR) {
          BindingDescriptor binding = (BindingDescriptor) domain;
          if (binding.adapterKind() != AdapterKind.MOCK) {
            findings.add(
                finding(
                    GovernanceValidationCategory.SECURITY,
                    GovernanceValidationSeverity.ERROR,
                    "NON_MOCK_BINDING",
                    "Only MOCK binding eligible",
                    ref.toString()));
          }
        }
        if (ref.artifactType() == GovernanceArtifactType.DATA_PROTECTION_PROFILE) {
          br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition dp =
              (br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition) domain;
          if (dp.purpose()
              != br.com.banco.spider.security.dataprotection.DataProtectionPurpose
                  .EXTERNAL_SIGNAL_ENVELOPE_AT_REST) {
            findings.add(
                finding(
                    GovernanceValidationCategory.SECURITY,
                    GovernanceValidationSeverity.ERROR,
                    "DP_PURPOSE_INVALID",
                    "Data protection purpose must be EXTERNAL_SIGNAL_ENVELOPE_AT_REST",
                    ref.toString()));
          }
          if (dp.algorithm()
              != br.com.banco.spider.security.dataprotection.DataProtectionAlgorithm.AES_256_GCM) {
            findings.add(
                finding(
                    GovernanceValidationCategory.SECURITY,
                    GovernanceValidationSeverity.ERROR,
                    "DP_ALGORITHM_INVALID",
                    "Only AES_256_GCM allowed",
                    ref.toString()));
          }
        }
        if (ref.artifactType() == GovernanceArtifactType.EXTERNAL_SIGNAL_DEFINITION) {
          br.com.banco.spider.execution.signal.ExternalSignalDefinition signal =
              (br.com.banco.spider.execution.signal.ExternalSignalDefinition) domain;
          if (signal.dataProtectionProfileRef() != null) {
            boolean found = false;
            for (GovernanceArtifactRef other : bundle.artifactRefs()) {
              if (other.artifactType() == GovernanceArtifactType.DATA_PROTECTION_PROFILE
                  && other.exactRef().equals(signal.dataProtectionProfileRef())) {
                found = true;
                break;
              }
              // also accept dp:code@version form matching artifact exactRef
              if (other.artifactType() == GovernanceArtifactType.DATA_PROTECTION_PROFILE) {
                GovernanceArtifact dpArt = artifactStore.findByRef(other).orElse(null);
                if (dpArt != null) {
                  try {
                    var dp =
                        (br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition)
                            codecs.decode(
                                other.artifactType(),
                                dpArt.canonicalContent(),
                                codecs.domainClass(other.artifactType()));
                    if (dp.exactRef().equals(signal.dataProtectionProfileRef())
                        || other.exactRef().equals(signal.dataProtectionProfileRef())) {
                      found = true;
                      break;
                    }
                  } catch (RuntimeException ignored) {
                    // codec failure already reported elsewhere
                  }
                }
              }
            }
            if (!found) {
              findings.add(
                  finding(
                      GovernanceValidationCategory.REFERENTIAL,
                      GovernanceValidationSeverity.ERROR,
                      "SIGNAL_DP_PROFILE_MISSING",
                      "Signal Definition references missing Data Protection Profile",
                      signal.dataProtectionProfileRef()));
            }
          }
        }
      } catch (IllegalArgumentException ex) {
        findings.add(
            finding(
                GovernanceValidationCategory.STRUCTURAL,
                GovernanceValidationSeverity.ERROR,
                "CODEC_FAILED",
                "Codec/decode failed",
                ref.toString()));
      }
    }
    if (!bundle.artifactRefs().isEmpty() && routes == 0) {
      findings.add(
          finding(
              GovernanceValidationCategory.OPERABILITY,
              GovernanceValidationSeverity.ERROR,
              "NO_PUBLISHABLE_ROUTE",
              "Non-empty bundle requires at least one route",
              bundle.exactRef()));
    }
    int errors =
        (int)
            findings.stream()
                .filter(f -> f.severity() == GovernanceValidationSeverity.ERROR)
                .count();
    int warnings =
        (int)
            findings.stream()
                .filter(f -> f.severity() == GovernanceValidationSeverity.WARNING)
                .count();
    int infos =
        (int)
            findings.stream()
                .filter(f -> f.severity() == GovernanceValidationSeverity.INFO)
                .count();
    return new GovernanceValidationReport(
        ids.nextId("gvrep"),
        bundle.bundleId(),
        VALIDATOR_VERSION,
        errors == 0,
        errors,
        warnings,
        infos,
        findings,
        clock.now(),
        actorPrincipalRef);
  }

  private static GovernanceValidationFinding finding(
      GovernanceValidationCategory cat,
      GovernanceValidationSeverity sev,
      String code,
      String message,
      String target) {
    return new GovernanceValidationFinding(cat, sev, code, message, target);
  }
}
