package br.com.segsense.inbound.http.demonstration;

import java.util.List;

public record PublicDemonstrationResponse(
    String key,
    String title,
    String summary,
    String intendedAudience,
    String scopeNote,
    int revisionNumber,
    String publishedAt,
    List<Block> blocks,
    List<Reference> references) {

  public record Block(int position, String title, String body) {}

  public record Reference(String url, String consultedOn, String verificationStatus) {}
}
