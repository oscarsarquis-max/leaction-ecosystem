package br.com.segsense.inbound.http.link;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record IssuedContextLinkResponse(
    UUID id,
    String placementKey,
    String label,
    String status,
    String effectiveStatus,
    int revisionNumber,
    Instant issuedAt,
    String issuedBy,
    Instant expiresAt,
    long version,
    String token,
    String publicUrl,
    String tokenHint,
    List<ContextLinkBindingResponse> publisherContext) {}
