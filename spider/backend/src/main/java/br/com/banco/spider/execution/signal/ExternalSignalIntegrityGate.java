package br.com.banco.spider.execution.signal;

import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import br.com.banco.spider.security.integrity.CanonicalPayloadDigestService;
import br.com.banco.spider.security.integrity.IntegrityProfileCatalogPort;
import br.com.banco.spider.security.integrity.IntegrityProfileDefinition;
import br.com.banco.spider.security.integrity.IntegrityProof;
import br.com.banco.spider.security.integrity.IntegrityPurpose;
import br.com.banco.spider.security.integrity.IntegrityVerificationDisposition;
import br.com.banco.spider.security.integrity.MessageIntegrityService;
import br.com.banco.spider.security.integrity.SigningInputCanonicalizerV1;
import br.com.banco.spider.security.integrity.SigningMaterial;
import br.com.banco.spider.security.replay.ReplayDecision;
import br.com.banco.spider.security.replay.ReplayDecisionStatus;
import br.com.banco.spider.security.replay.ReplayGuardPort;
import br.com.banco.spider.security.replay.ReplayReservation;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

/**
 * Gate de integridade + anti-replay para sinais. No-op quando integrity/replay desabilitados.
 */
@Component
public class ExternalSignalIntegrityGate {

  private static final Logger log = LoggerFactory.getLogger(ExternalSignalIntegrityGate.class);

  private final boolean integrityEnabled;
  private final boolean replayEnabled;
  private final ObjectProvider<MessageIntegrityService> integrityService;
  private final IntegrityProfileCatalogPort profileCatalog;
  private final ObjectProvider<ReplayGuardPort> replayGuard;
  private final CanonicalPayloadDigestService digestService;
  private final Sha256IdempotencyKeyHash sha256;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;

  public ExternalSignalIntegrityGate(
      @Value("${spider.security.integrity.enabled:false}") boolean integrityEnabled,
      @Value("${spider.security.replay-guard.enabled:false}") boolean replayEnabled,
      ObjectProvider<MessageIntegrityService> integrityService,
      IntegrityProfileCatalogPort profileCatalog,
      ObjectProvider<ReplayGuardPort> replayGuard,
      CanonicalPayloadDigestService digestService,
      Sha256IdempotencyKeyHash sha256,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this.integrityEnabled = integrityEnabled;
    this.replayEnabled = replayEnabled;
    this.integrityService = integrityService;
    this.profileCatalog = profileCatalog;
    this.replayGuard = replayGuard;
    this.digestService = digestService;
    this.sha256 = sha256;
    this.ids = ids;
    this.clock = clock;
  }

  public record GateResult(boolean allowed, String reasonCode, boolean duplicateSameMessage) {}

  public Mono<GateResult> evaluate(ExternalSignalEnvelope signal) {
    return evaluate(signal, null);
  }

  /**
   * Quando {@code ingressContext} está presente, o profile autoritativo é o histórico fixado —
   * claims do envelope devem coincidir; active catalog não é usado.
   */
  public Mono<GateResult> evaluate(
      ExternalSignalEnvelope signal, ExternalSignalIngressContext ingressContext) {
    if (!integrityEnabled) {
      return Mono.just(new GateResult(true, "INTEGRITY_DISABLED", false));
    }
    MessageIntegrityService mis = integrityService.getIfAvailable();
    if (mis == null) {
      log.info("event=integrity_verify_failure reasonCode=PROVIDER_MISSING");
      return Mono.just(new GateResult(false, "CRYPTOGRAPHIC_OPERATION_FAILED", false));
    }
    IntegrityProof proof = signal.integrityProof();
    IntegrityProfileCatalogPort catalog =
        ingressContext != null
            ? ingressContext.resolutionContext().integrityProfileCatalog()
            : profileCatalog;
    String authoritativeProfileRef =
        ingressContext != null
            ? ingressContext.integrityProfileRef()
            : signal.securityContext().securityProfileRef();
    if (ingressContext != null
        && signal.securityContext().securityProfileRef() != null
        && !authoritativeProfileRef.equals(signal.securityContext().securityProfileRef())) {
      log.info("event=contract_event_profile_mismatch reasonCode=CALLER_PROFILE");
      return Mono.just(new GateResult(false, "INTEGRITY_PROFILE_NOT_ALLOWED", false));
    }
    if (ingressContext != null) {
      log.info("event=active_snapshot_ignored_for_existing_wait reasonCode=HISTORICAL");
    }
    IntegrityProfileDefinition profile =
        catalog
            .findPublished(authoritativeProfileRef, IntegrityPurpose.EXTERNAL_SIGNAL)
            .orElse(null);
    if (profile == null) {
      return Mono.just(new GateResult(false, "INTEGRITY_PROFILE_NOT_ALLOWED", false));
    }
    if (proof == null) {
      return Mono.just(new GateResult(false, "INVALID_INTEGRITY_PROOF", false));
    }
    if (proof.profileRef() != null && !authoritativeProfileRef.equals(proof.profileRef())) {
      return Mono.just(new GateResult(false, "INTEGRITY_PROFILE_NOT_ALLOWED", false));
    }
    String payloadDigest =
        digestService.digestUtf8(
            signal.messageId() + "|" + signal.completion().disposition().name(),
            profile.maximumPayloadDigestBytes());
    SigningMaterial material =
        new SigningMaterial(
            SigningInputCanonicalizerV1.DOMAIN_EXTERNAL_SIGNAL,
            proof.profileRef(),
            proof.algorithm(),
            proof.keyRef(),
            proof.keyVersion(),
            signal.contractRef(),
            signal.completion().disposition().name(),
            signal.executionId(),
            signal.messageId(),
            0,
            proof.issuedAt(),
            proof.expiresAt(),
            proof.nonce(),
            proof.payloadDigestAlgorithm(),
            proof.payloadDigest(),
            proof.canonicalizationVersion());
    if (!digestService.secureEquals(payloadDigest, proof.payloadDigest())) {
      return Mono.just(new GateResult(false, "PAYLOAD_DIGEST_MISMATCH", false));
    }
    return mis.verify(material, proof)
        .flatMap(
            result -> {
              if (!result.verified()) {
                String code =
                    switch (result.disposition()) {
                      case EXPIRED -> "INTEGRITY_PROOF_EXPIRED";
                      case ISSUED_IN_FUTURE -> "INTEGRITY_TIMESTAMP_INVALID";
                      case INVALID_MAC, MALFORMED_PROOF -> "INVALID_INTEGRITY_PROOF";
                      default -> "CRYPTOGRAPHIC_OPERATION_FAILED";
                    };
                log.info("event=integrity_verify_failure reasonCode={}", code);
                return Mono.just(new GateResult(false, code, false));
              }
              if (!replayEnabled) {
                log.info("event=integrity_verified reasonCode=VERIFIED");
                return Mono.just(new GateResult(true, "VERIFIED", false));
              }
              ReplayGuardPort guard = replayGuard.getIfAvailable();
              if (guard == null) {
                return Mono.just(new GateResult(true, "VERIFIED", false));
              }
              Instant now = clock.now();
              String scopeHash = sha256.hash("signal:" + signal.sourceRef());
              String nonceHash = sha256.hash(proof.nonce());
              String msgFp = sha256.hash(signal.messageId() + "|" + payloadDigest);
              ReplayReservation candidate =
                  new ReplayReservation(
                      ids.nextId("rpl"),
                      scopeHash,
                      nonceHash,
                      msgFp,
                      "v1",
                      proof.keyRef(),
                      proof.keyVersion(),
                      authoritativeProfileRef,
                      now,
                      proof.expiresAt(),
                      ReplayDecisionStatus.RESERVED,
                      0L);
              ReplayDecision decision = guard.reserve(candidate);
              return switch (decision.status()) {
                case RESERVED -> {
                  log.info("event=replay_reservation_won reasonCode=RESERVED");
                  yield Mono.just(new GateResult(true, "VERIFIED", false));
                }
                case DUPLICATE_SAME_MESSAGE -> {
                  log.info("event=duplicate_same_message reasonCode=DUPLICATE");
                  yield Mono.just(new GateResult(true, "DUPLICATE_SAME_MESSAGE", true));
                }
                case REPLAY_CONFLICT -> {
                  log.info("event=replay_conflict reasonCode=CONFLICT");
                  yield Mono.just(new GateResult(false, "REPLAY_CONFLICT", false));
                }
                case EXPIRED_PROOF -> Mono.just(new GateResult(false, "INTEGRITY_PROOF_EXPIRED", false));
                case CAPACITY_REJECTED ->
                    Mono.just(new GateResult(false, "CRYPTOGRAPHIC_OPERATION_FAILED", false));
              };
            });
  }
}
