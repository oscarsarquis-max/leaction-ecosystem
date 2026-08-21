package br.com.banco.spider.execution.callback;

import br.com.banco.spider.security.integrity.CanonicalPayloadDigestService;
import br.com.banco.spider.security.integrity.IntegrityProfileCatalogPort;
import br.com.banco.spider.security.integrity.IntegrityProfileDefinition;
import br.com.banco.spider.security.integrity.IntegrityProof;
import br.com.banco.spider.security.integrity.IntegrityPurpose;
import br.com.banco.spider.security.integrity.MessageIntegrityService;
import br.com.banco.spider.security.integrity.SigningInputCanonicalizerV1;
import br.com.banco.spider.security.integrity.SigningMaterial;
import br.com.banco.spider.execution.support.SpiderClock;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

@Component
public class CallbackIntegritySupport {

  private static final Logger log = LoggerFactory.getLogger(CallbackIntegritySupport.class);

  private final boolean integrityEnabled;
  private final ObjectProvider<MessageIntegrityService> integrityService;
  private final IntegrityProfileCatalogPort profileCatalog;
  private final CanonicalPayloadDigestService digestService;
  private final SpiderClock clock;

  public CallbackIntegritySupport(
      @Value("${spider.security.integrity.enabled:false}") boolean integrityEnabled,
      ObjectProvider<MessageIntegrityService> integrityService,
      IntegrityProfileCatalogPort profileCatalog,
      CanonicalPayloadDigestService digestService,
      SpiderClock clock) {
    this.integrityEnabled = integrityEnabled;
    this.integrityService = integrityService;
    this.profileCatalog = profileCatalog;
    this.digestService = digestService;
    this.clock = clock;
  }

  public boolean enabled() {
    return integrityEnabled && integrityService.getIfAvailable() != null;
  }

  public Mono<Optional<IntegrityProof>> signDelivery(
      ExecutionCallbackContext ctx,
      CallbackOutboxRecord outbox,
      int attemptNumber,
      JsonNode payload) {
    if (!enabled()) {
      return Mono.just(Optional.empty());
    }
    MessageIntegrityService mis = integrityService.getObject();
    IntegrityProfileDefinition profile =
        profileCatalog
            .findPublished(ctx.securityProfileRef(), IntegrityPurpose.CALLBACK_DELIVERY)
            .orElse(null);
    if (profile == null) {
      log.info("event=callback_signing_blocked reasonCode=INTEGRITY_PROFILE_NOT_FOUND");
      return Mono.error(new IllegalStateException("INTEGRITY_PROFILE_NOT_FOUND"));
    }
    Instant now = clock.now();
    String payloadDigest =
        digestService.digestUtf8(payload.toString(), profile.maximumPayloadDigestBytes());
    String nonce = mis.newNonce();
    SigningMaterial material =
        new SigningMaterial(
            SigningInputCanonicalizerV1.DOMAIN_CALLBACK_DELIVERY,
            profile.exactRef(),
            profile.algorithm(),
            profile.signingKeyRef(),
            profile.activeSigningKeyVersion(),
            ctx.callbackContractRef(),
            "CALLBACK_DELIVERY",
            outbox.executionId(),
            outbox.logicalCallbackId(),
            attemptNumber,
            now,
            now.plus(profile.replayWindow()),
            nonce,
            CanonicalPayloadDigestService.ALGORITHM,
            payloadDigest,
            profile.canonicalizationVersion());
    return mis.sign(material, profile).map(Optional::of);
  }

  public Mono<Optional<IntegrityProof>> signStatusQuery(
      ExecutionCallbackContext ctx,
      String deliveryKey,
      int queryAttempt,
      Instant deadline) {
    if (!enabled()) {
      return Mono.just(Optional.empty());
    }
    MessageIntegrityService mis = integrityService.getObject();
    IntegrityProfileDefinition profile =
        profileCatalog
            .findPublished(ctx.securityProfileRef(), IntegrityPurpose.CALLBACK_STATUS_QUERY)
            .or(() ->
                profileCatalog.findPublished(
                    ctx.securityProfileRef(), IntegrityPurpose.CALLBACK_DELIVERY))
            .orElse(null);
    if (profile == null) {
      // Status query signing optional unless dedicated profile exists
      return Mono.just(Optional.empty());
    }
    Instant now = clock.now();
    String digest =
        digestService.digestUtf8(
            deliveryKey + "|" + queryAttempt, profile.maximumPayloadDigestBytes());
    SigningMaterial material =
        new SigningMaterial(
            SigningInputCanonicalizerV1.DOMAIN_STATUS_QUERY,
            profile.exactRef(),
            profile.algorithm(),
            profile.signingKeyRef(),
            profile.activeSigningKeyVersion(),
            ctx.callbackContractRef(),
            "CALLBACK_STATUS_QUERY",
            ctx.executionId(),
            deliveryKey,
            queryAttempt,
            now,
            deadline.isBefore(now.plus(Duration.ofSeconds(1)))
                ? now.plus(Duration.ofSeconds(1))
                : deadline,
            mis.newNonce(),
            CanonicalPayloadDigestService.ALGORITHM,
            digest,
            profile.canonicalizationVersion());
    return mis.sign(material, profile).map(Optional::of);
  }
}
