package br.com.segsense.inbound.http.opportunity;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record OpportunityRevisionSnapshotResponse(
    UUID id,
    int revisionNumber,
    Instant createdAt,
    String createdBy,
    String title,
    String contextMode,
    String contextSummaryTemplate,
    String objectiveTemplate,
    String callToActionLabel,
    Instant validFrom,
    Instant validUntil,
    List<ContextFieldResponse> contextFields) {}
