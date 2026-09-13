package br.com.segsense.inbound.http.catalog;

import java.time.Instant;
import java.util.UUID;

public record PublisherResponse(
    UUID id,
    String key,
    String name,
    String status,
    long version,
    Instant createdAt,
    Instant updatedAt,
    String createdBy,
    String updatedBy,
    boolean effectivelyAvailable) {}
