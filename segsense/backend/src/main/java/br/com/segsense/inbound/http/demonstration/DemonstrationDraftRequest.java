package br.com.segsense.inbound.http.demonstration;

import java.util.List;

public record DemonstrationDraftRequest(
    String title,
    String summary,
    String intendedAudience,
    String scopeNote,
    Long version,
    String justification,
    List<BlockRequest> blocks,
    List<ClaimRequest> claims) {

  public record BlockRequest(String title, String body) {}

  public record ClaimRequest(String text, String sourceKey) {}
}
