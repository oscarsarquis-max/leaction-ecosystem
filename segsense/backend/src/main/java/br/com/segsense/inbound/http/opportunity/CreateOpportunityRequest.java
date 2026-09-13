package br.com.segsense.inbound.http.opportunity;

import java.util.List;

public record CreateOpportunityRequest(
    String key,
    String title,
    String contextMode,
    String contextSummaryTemplate,
    String objectiveTemplate,
    String callToActionLabel,
    String validFrom,
    String validUntil,
    List<ContextFieldRequest> contextFields) {}
