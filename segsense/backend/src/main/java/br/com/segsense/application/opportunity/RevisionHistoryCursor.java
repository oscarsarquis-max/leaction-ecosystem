package br.com.segsense.application.opportunity;

import br.com.segsense.domain.catalog.CatalogValidationException;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.UUID;

public record RevisionHistoryCursor(UUID opportunityId, int revisionNumber) {

  private static final Base64.Encoder ENCODER = Base64.getUrlEncoder().withoutPadding();
  private static final Base64.Decoder DECODER = Base64.getUrlDecoder();

  public static String encode(UUID opportunityId, int revisionNumber) {
    String payload = opportunityId + "|" + revisionNumber;
    return ENCODER.encodeToString(payload.getBytes(StandardCharsets.UTF_8));
  }

  public static RevisionHistoryCursor decode(String raw, UUID expectedOpportunityId) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("O cursor informado é inválido.");
    }
    try {
      String payload = new String(DECODER.decode(raw), StandardCharsets.UTF_8);
      int separator = payload.indexOf('|');
      UUID opportunityId = UUID.fromString(payload.substring(0, separator));
      int revisionNumber = Integer.parseInt(payload.substring(separator + 1));
      if (!opportunityId.equals(expectedOpportunityId) || revisionNumber < 1) {
        throw new CatalogValidationException("O cursor informado é inválido.");
      }
      return new RevisionHistoryCursor(opportunityId, revisionNumber);
    } catch (CatalogValidationException ex) {
      throw ex;
    } catch (RuntimeException ex) {
      throw new CatalogValidationException("O cursor informado é inválido.");
    }
  }
}
