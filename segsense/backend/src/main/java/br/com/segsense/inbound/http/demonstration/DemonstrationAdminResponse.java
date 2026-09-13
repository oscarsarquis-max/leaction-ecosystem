package br.com.segsense.inbound.http.demonstration;

import java.util.List;
import java.util.UUID;

public record DemonstrationAdminResponse(
    UUID id,
    String key,
    String workflowStatus,
    String publicationStatus,
    int currentRevision,
    Integer publishedRevision,
    long version,
    String title,
    String summary,
    String intendedAudience,
    String scopeNote,
    boolean frozen,
    List<Block> blocks,
    List<Claim> claims,
    boolean administrativePreview) {

  public record Block(int position, String title, String body) {}

  public record Claim(int position, String text, UUID sourceId) {}
}
