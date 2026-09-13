package br.com.segsense.inbound.http.demonstration;

import java.util.List;

public record CreateDemonstrationRequest(
    String key,
    String title,
    String summary,
    String intendedAudience,
    String scopeNote,
    List<DemonstrationDraftRequest.BlockRequest> blocks,
    List<DemonstrationDraftRequest.ClaimRequest> claims) {}
