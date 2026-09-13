package br.com.segsense.inbound.http.catalog;

import java.time.Instant;
import java.util.UUID;

public record ChannelResponse(
    UUID id,
    UUID publisherId,
    String key,
    String name,
    String type,
    String status,
    long version,
    Instant createdAt,
    Instant updatedAt,
    String createdBy,
    String updatedBy,
    boolean effectivelyAvailable) {}
