package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.CatalogValidationException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.UUID;

public record CatalogCursor(Instant createdAt, UUID id) {

  private static final Base64.Encoder ENCODER = Base64.getUrlEncoder().withoutPadding();
  private static final Base64.Decoder DECODER = Base64.getUrlDecoder();

  public static String encode(Instant createdAt, UUID id) {
    String payload = createdAt + "|" + id;
    return ENCODER.encodeToString(payload.getBytes(StandardCharsets.UTF_8));
  }

  public static CatalogCursor decode(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("O cursor informado é inválido.");
    }
    try {
      String payload = new String(DECODER.decode(raw), StandardCharsets.UTF_8);
      int separator = payload.indexOf('|');
      if (separator <= 0 || separator == payload.length() - 1) {
        throw new CatalogValidationException("O cursor informado é inválido.");
      }
      Instant createdAt = Instant.parse(payload.substring(0, separator));
      UUID id = UUID.fromString(payload.substring(separator + 1));
      return new CatalogCursor(createdAt, id);
    } catch (CatalogValidationException ex) {
      throw ex;
    } catch (RuntimeException ex) {
      throw new CatalogValidationException("O cursor informado é inválido.");
    }
  }
}
