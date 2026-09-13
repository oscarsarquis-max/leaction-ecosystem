package br.com.segsense.inbound.http.link;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record ContextLinkResponse(
    UUID id,
    String placementKey,
    String label,
    String status,
    String effectiveStatus,
    int revisionNumber,
    Instant issuedAt,
    String issuedBy,
    Instant expiresAt,
    Instant revokedAt,
    String revokedBy,
    String revocationReason,
    long version,
    String tokenHint,
    List<ContextLinkBindingResponse> publisherContext) {}
