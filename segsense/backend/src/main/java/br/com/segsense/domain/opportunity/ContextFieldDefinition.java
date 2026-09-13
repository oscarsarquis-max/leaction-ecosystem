package br.com.segsense.domain.opportunity;

import br.com.segsense.domain.catalog.CatalogValidationException;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.regex.Pattern;

public final class ContextFieldDefinition {

  private static final Pattern KEY_PATTERN = Pattern.compile("^[a-z][a-zA-Z0-9]{1,39}$");

  private final String key;
  private final String label;
  private final ContextFieldType type;
  private final boolean required;
  private final ContextFieldSource source;
  private final FieldClassification classification;
  private final List<String> allowedValues;
  private final int position;

  private ContextFieldDefinition(
      String key,
      String label,
      ContextFieldType type,
      boolean required,
      ContextFieldSource source,
      FieldClassification classification,
      List<String> allowedValues,
      int position) {
    this.key = key;
    this.label = label;
    this.type = type;
    this.required = required;
    this.source = source;
    this.classification = classification;
    this.allowedValues = allowedValues;
    this.position = position;
  }

  public static ContextFieldDefinition parse(
      String rawKey,
      String rawLabel,
      ContextFieldType type,
      boolean required,
      ContextFieldSource source,
      FieldClassification classification,
      List<String> rawAllowedValues,
      int position) {
    if (rawKey == null || rawKey.isBlank()) {
      throw new CatalogValidationException("A chave do campo é obrigatória.");
    }
    String key = rawKey.trim();
    if (!KEY_PATTERN.matcher(key).matches()) {
      throw new CatalogValidationException(
          "A chave do campo deve começar com letra minúscula e conter apenas letras ou números.");
    }
    OpportunityText.rejectPersonalIdentifier(key, "A chave do campo");
    String label = OpportunityText.requiredLength(rawLabel, "O rótulo do campo", 3, 80);
    OpportunityText.rejectPersonalIdentifier(label, "O rótulo do campo");
    Objects.requireNonNull(type, "type");
    Objects.requireNonNull(source, "source");
    if (classification != FieldClassification.NON_PERSONAL) {
      throw new CatalogValidationException("A classificação do campo deve ser NON_PERSONAL.");
    }
    if (position < 0 || position > 19) {
      throw new CatalogValidationException("A ordem dos campos deve estar entre 0 e 19.");
    }
    List<String> allowed = List.of();
    if (type == ContextFieldType.ENUM) {
      if (rawAllowedValues == null || rawAllowedValues.isEmpty() || rawAllowedValues.size() > 50) {
        throw new CatalogValidationException("Campo ENUM exige de 1 a 50 valores permitidos.");
      }
      List<String> parsed = new ArrayList<>();
      for (String raw : rawAllowedValues) {
        String value = OpportunityText.requiredLength(raw, "O valor permitido", 1, 80);
        OpportunityText.rejectPersonalIdentifier(value, "O valor permitido");
        if (parsed.stream().anyMatch(existing -> existing.equalsIgnoreCase(value))) {
          throw new CatalogValidationException("Os valores permitidos do ENUM não podem se repetir.");
        }
        parsed.add(value);
      }
      allowed = List.copyOf(parsed);
    } else if (rawAllowedValues != null && !rawAllowedValues.isEmpty()) {
      throw new CatalogValidationException("Somente campos ENUM admitem valores permitidos.");
    }
    return new ContextFieldDefinition(
        key, label, type, required, source, FieldClassification.NON_PERSONAL, allowed, position);
  }

  public String key() {
    return key;
  }

  public String label() {
    return label;
  }

  public ContextFieldType type() {
    return type;
  }

  public boolean required() {
    return required;
  }

  public ContextFieldSource source() {
    return source;
  }

  public FieldClassification classification() {
    return classification;
  }

  public List<String> allowedValues() {
    return allowedValues;
  }

  public int position() {
    return position;
  }
}
