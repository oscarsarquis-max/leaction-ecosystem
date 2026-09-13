package br.com.segsense.inbound.http.opportunity;

import java.util.List;

public record CreateOpportunityRevisionRequest(
    Long expectedVersion,
    Integer baseRevision,
    String title,
    String contextMode,
    String contextSummaryTemplate,
    String objectiveTemplate,
    String callToActionLabel,
    String validFrom,
    String validUntil,
    List<ContextFieldRequest> contextFields) {}
