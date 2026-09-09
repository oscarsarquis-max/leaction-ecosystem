package br.com.banco.spider.contextuallink.domain;

import java.net.URI;
import java.time.Instant;
import java.util.List;
import java.util.Objects;

public record ContextualLinkSession(
    ClickContext click,
    PageContext page,
    CorrelationChain correlation,
    BoundaryFlags boundary,
    List<ProvenanceStep> provenance,
    String gatewayUrl,
    URI redirectTo,
    Instant completedAt) {

  public ContextualLinkSession {
    Objects.requireNonNull(click, "click");
    Objects.requireNonNull(page, "page");
    Objects.requireNonNull(correlation, "correlation");
    Objects.requireNonNull(boundary, "boundary");
    provenance = provenance == null ? List.of() : List.copyOf(provenance);
    Objects.requireNonNull(gatewayUrl, "gatewayUrl");
    Objects.requireNonNull(redirectTo, "redirectTo");
    Objects.requireNonNull(completedAt, "completedAt");
  }

  public ContextualLinkSession withCorrelation(CorrelationChain next, BoundaryFlags nextBoundary) {
    return new ContextualLinkSession(
        click, page, next, nextBoundary, provenance, gatewayUrl, redirectTo, completedAt);
  }
}
