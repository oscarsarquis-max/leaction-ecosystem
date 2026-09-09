package br.com.banco.spider.contextuallink.domain;

import java.time.Instant;
import java.util.Objects;

/**
 * Contexto do clique. Ainda não é Intent empresarial.
 */
public record ClickContext(
    String clickId,
    Instant createdAt,
    String sourceType,
    String referrer,
    String referrerOrigin,
    ReferrerAvailability referrerAvailability,
    ContextAcquisitionStatus contextAcquisitionStatus,
    String contextId) {

  public static final String SOURCE_TYPE = "CONTEXTUAL_LINK";

  public ClickContext {
    Objects.requireNonNull(clickId, "clickId");
    Objects.requireNonNull(createdAt, "createdAt");
    Objects.requireNonNull(sourceType, "sourceType");
    Objects.requireNonNull(referrerAvailability, "referrerAvailability");
    Objects.requireNonNull(contextAcquisitionStatus, "contextAcquisitionStatus");
    Objects.requireNonNull(contextId, "contextId");
    if (!clickId.startsWith("clk-")) {
      throw new IllegalArgumentException("clickId must be opaque clk- token");
    }
    if (!contextId.startsWith("ctx-")) {
      throw new IllegalArgumentException("contextId must be opaque ctx- token");
    }
  }
}
