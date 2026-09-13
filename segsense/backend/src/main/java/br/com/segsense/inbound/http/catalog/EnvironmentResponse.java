package br.com.segsense.inbound.http.catalog;

import java.time.Instant;
import java.util.UUID;

public record EnvironmentResponse(
    UUID id,
    UUID publisherId,
    UUID channelId,
    String key,
    String name,
    String type,
    String canonicalUrl,
    String status,
    long version,
    Instant createdAt,
    Instant updatedAt,
    String createdBy,
    String updatedBy,
    boolean effectivelyAvailable) {}
