package br.com.segsense.domain.demonstration;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record DemonstrationRevision(
    UUID id,
    int revisionNumber,
    String title,
    String summary,
    String intendedAudience,
    String scopeNote,
    boolean frozen,
    Instant createdAt,
    String createdBy,
    List<DemonstrationBlock> blocks,
    List<DemonstrationClaim> claims) {

  public DemonstrationRevision {
    title = DemonstrationText.required(title, "O título", 3, 200);
    summary = DemonstrationText.required(summary, "O resumo", 10, 1000);
    intendedAudience = DemonstrationText.required(intendedAudience, "O público pretendido", 3, 200);
    scopeNote = DemonstrationText.required(scopeNote, "A nota de escopo", 10, 1000);
    blocks = List.copyOf(blocks);
    claims = List.copyOf(claims);
  }
}
