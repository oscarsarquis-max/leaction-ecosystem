package br.com.segsense.application.opportunity;

import br.com.segsense.domain.catalog.CatalogValidationException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.UUID;

public record LifecycleEventCursor(UUID opportunityId, Instant occurredAt, UUID id) {

  private static final Base64.Encoder ENCODER = Base64.getUrlEncoder().withoutPadding();
  private static final Base64.Decoder DECODER = Base64.getUrlDecoder();

  public static String encode(UUID opportunityId, Instant occurredAt, UUID id) {
    String payload = opportunityId + "|" + occurredAt + "|" + id;
    return ENCODER.encodeToString(payload.getBytes(StandardCharsets.UTF_8));
  }

  public static LifecycleEventCursor decode(String raw, UUID expectedOpportunityId) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("O cursor informado é inválido.");
    }
    try {
      String payload = new String(DECODER.decode(raw), StandardCharsets.UTF_8);
      String[] parts = payload.split("\\|", 3);
      if (parts.length != 3) {
        throw new CatalogValidationException("O cursor informado é inválido.");
      }
      UUID opportunityId = UUID.fromString(parts[0]);
      Instant occurredAt = Instant.parse(parts[1]);
      UUID id = UUID.fromString(parts[2]);
      if (!opportunityId.equals(expectedOpportunityId)) {
        throw new CatalogValidationException("O cursor informado é inválido.");
      }
      return new LifecycleEventCursor(opportunityId, occurredAt, id);
    } catch (CatalogValidationException ex) {
      throw ex;
    } catch (RuntimeException ex) {
      throw new CatalogValidationException("O cursor informado é inválido.");
    }
  }
}
