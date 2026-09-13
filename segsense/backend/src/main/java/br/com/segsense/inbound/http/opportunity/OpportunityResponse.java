package br.com.segsense.inbound.http.opportunity;

import java.time.Instant;
import java.util.UUID;

public record OpportunityResponse(
    UUID id,
    UUID publisherId,
    UUID channelId,
    UUID environmentId,
    String key,
    String status,
    int currentRevision,
    Integer submittedRevision,
    Integer approvedRevision,
    long version,
    Instant createdAt,
    Instant updatedAt,
    String createdBy,
    String updatedBy,
    boolean effectivelyAvailable,
    boolean effectivelyPublishable,
    boolean effectivelyPublished,
    OpportunityRevisionSnapshotResponse current) {}
