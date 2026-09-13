package br.com.segsense.domain.demonstration;

import java.util.UUID;

public record DemonstrationClaim(UUID id, int position, String text, UUID sourceId) {

  public DemonstrationClaim {
    if (position < 1) {
      throw new IllegalArgumentException("position");
    }
    text = DemonstrationText.required(text, "A alegação", 10, 500);
    if (sourceId == null) {
      throw new IllegalArgumentException("sourceId");
    }
  }
}
