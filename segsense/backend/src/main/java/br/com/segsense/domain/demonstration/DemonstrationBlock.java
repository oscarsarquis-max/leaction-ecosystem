package br.com.segsense.domain.demonstration;

import java.util.UUID;

public record DemonstrationBlock(UUID id, int position, String title, String body) {

  public DemonstrationBlock {
    if (position < 1) {
      throw new IllegalArgumentException("position");
    }
    title = DemonstrationText.required(title, "O título do bloco", 3, 200);
    body = DemonstrationText.required(body, "O texto do bloco", 3, 4000);
  }
}
