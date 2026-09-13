package br.com.segsense.domain.link;

import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.opportunity.OpportunityText;
import java.util.regex.Pattern;

public final class PlacementKey {

  private static final Pattern PATTERN = Pattern.compile("^[a-z][a-z0-9-]{2,79}$");

  private PlacementKey() {}

  public static String parse(String raw) {
    String value = OpportunityText.requiredLength(raw, "A chave de posicionamento", 3, 80);
    if (!PATTERN.matcher(value).matches()) {
      throw new CatalogValidationException(
          "A chave de posicionamento deve começar com letra minúscula e usar apenas letras, números ou hífen.");
    }
    OpportunityText.rejectPersonalIdentifier(value, "A chave de posicionamento");
    return value;
  }
}
