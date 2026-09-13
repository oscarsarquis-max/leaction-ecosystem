package br.com.segsense.application.link;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.UUID;

import br.com.segsense.domain.catalog.CatalogValidationException;

public record ContextLinkCursor(Instant issuedAt, UUID id) {

  private static final Base64.Encoder ENCODER = Base64.getUrlEncoder().withoutPadding();
  private static final Base64.Decoder DECODER = Base64.getUrlDecoder();

  public static String encode(Instant issuedAt, UUID id) {
    String payload = issuedAt + "|" + id;
    return ENCODER.encodeToString(payload.getBytes(StandardCharsets.UTF_8));
  }

  public static ContextLinkCursor decode(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("O cursor informado é inválido.");
    }
    try {
      String payload = new String(DECODER.decode(raw), StandardCharsets.UTF_8);
      String[] parts = payload.split("\\|", 2);
      if (parts.length != 2) {
        throw new CatalogValidationException("O cursor informado é inválido.");
      }
      return new ContextLinkCursor(Instant.parse(parts[0]), UUID.fromString(parts[1]));
    } catch (CatalogValidationException ex) {
      throw ex;
    } catch (RuntimeException ex) {
      throw new CatalogValidationException("O cursor informado é inválido.");
    }
  }
}
