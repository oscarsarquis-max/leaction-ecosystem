package br.com.segsense.inbound.http.link;

import java.time.Instant;
import java.util.List;

public record IssueContextLinkRequest(
    String placementKey,
    String label,
    Instant expiresAt,
    List<PublisherContextBindingRequest> publisherContext) {

  public record PublisherContextBindingRequest(String fieldKey, Object value) {}
}
