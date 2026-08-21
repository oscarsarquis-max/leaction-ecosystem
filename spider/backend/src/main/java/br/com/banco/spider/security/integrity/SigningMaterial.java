package br.com.banco.spider.security.integrity;

import java.time.Instant;
import java.util.Objects;

/** Material a assinar/verificar — sem segredo. */
public record SigningMaterial(
    String domainSeparator,
    String profileRef,
    IntegrityAlgorithm algorithm,
    String keyRef,
    String keyVersion,
    String contractRef,
    String messageType,
    String executionOrCorrelationId,
    String deliveryOrMessageId,
    int attemptNumber,
    Instant issuedAt,
    Instant expiresAt,
    String nonce,
    String payloadDigestAlgorithm,
    String payloadDigest,
    SigningCanonicalizationVersion canonicalizationVersion) {

  public SigningMaterial {
    Objects.requireNonNull(domainSeparator, "domainSeparator");
    Objects.requireNonNull(profileRef, "profileRef");
    Objects.requireNonNull(algorithm, "algorithm");
    Objects.requireNonNull(keyRef, "keyRef");
    Objects.requireNonNull(keyVersion, "keyVersion");
    Objects.requireNonNull(canonicalizationVersion, "canonicalizationVersion");
    Objects.requireNonNull(issuedAt, "issuedAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
    Objects.requireNonNull(payloadDigestAlgorithm, "payloadDigestAlgorithm");
    Objects.requireNonNull(payloadDigest, "payloadDigest");
  }
}
