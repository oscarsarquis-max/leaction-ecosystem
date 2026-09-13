package br.com.segsense.domain.link;

import br.com.segsense.domain.opportunity.ContextFieldDefinition;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.OpportunityText;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.Objects;
import java.util.UUID;

public final class PublisherContextBinding {

  private static final BigDecimal MAX_ABS = new BigDecimal("1000000000000");

  private final UUID id;
  private final String fieldKey;
  private final ContextFieldType fieldType;
  private final ContextFieldSource fieldSource;
  private final String textValue;
  private final BigDecimal numberValue;
  private final Boolean booleanValue;
  private final LocalDate dateValue;

  private PublisherContextBinding(
      UUID id,
      String fieldKey,
      ContextFieldType fieldType,
      ContextFieldSource fieldSource,
      String textValue,
      BigDecimal numberValue,
      Boolean booleanValue,
      LocalDate dateValue) {
    this.id = id;
    this.fieldKey = fieldKey;
    this.fieldType = fieldType;
    if (fieldSource != ContextFieldSource.PUBLISHER && fieldSource != ContextFieldSource.EITHER) {
      throw new InvalidPublisherContextException();
    }
    this.fieldSource = fieldSource;
    this.textValue = textValue;
    this.numberValue = numberValue;
    this.booleanValue = booleanValue;
    this.dateValue = dateValue;
  }

  public static PublisherContextBinding text(UUID id, ContextFieldDefinition field, String raw) {
    requireCompatible(field, ContextFieldType.TEXT, ContextFieldType.ENUM);
    String value = OpportunityText.requiredLength(raw, "O valor do campo " + field.key(), 1, 200);
    OpportunityText.rejectPersonalIdentifier(value, "O valor do campo " + field.key());
    if (field.type() == ContextFieldType.ENUM && !field.allowedValues().contains(value)) {
      throw new InvalidPublisherContextException();
    }
    return new PublisherContextBinding(id, field.key(), field.type(), field.source(), value, null, null, null);
  }

  public static PublisherContextBinding number(UUID id, ContextFieldDefinition field, BigDecimal raw) {
    requireCompatible(field, ContextFieldType.NUMBER);
    if (raw == null || raw.abs().compareTo(MAX_ABS) > 0 || raw.scale() > 10) {
      throw new InvalidPublisherContextException();
    }
    BigDecimal canonical = raw.stripTrailingZeros();
    if (canonical.scale() < 0) {
      canonical = canonical.setScale(0, RoundingMode.UNNECESSARY);
    }
    return new PublisherContextBinding(id, field.key(), ContextFieldType.NUMBER, field.source(), null, canonical, null, null);
  }

  public static PublisherContextBinding bool(UUID id, ContextFieldDefinition field, Boolean raw) {
    requireCompatible(field, ContextFieldType.BOOLEAN);
    if (raw == null) {
      throw new InvalidPublisherContextException();
    }
    return new PublisherContextBinding(id, field.key(), ContextFieldType.BOOLEAN, field.source(), null, null, raw, null);
  }

  public static PublisherContextBinding date(UUID id, ContextFieldDefinition field, String raw) {
    requireCompatible(field, ContextFieldType.DATE);
    if (raw == null) {
      throw new InvalidPublisherContextException();
    }
    try {
      LocalDate parsed = LocalDate.parse(raw, DateTimeFormatter.ISO_LOCAL_DATE);
      return new PublisherContextBinding(id, field.key(), ContextFieldType.DATE, field.source(), null, null, null, parsed);
    } catch (DateTimeParseException exception) {
      throw new InvalidPublisherContextException();
    }
  }

  public static PublisherContextBinding restore(
      UUID id,
      String fieldKey,
      ContextFieldType fieldType,
      ContextFieldSource fieldSource,
      String textValue,
      BigDecimal numberValue,
      Boolean booleanValue,
      LocalDate dateValue) {
    return new PublisherContextBinding(
        Objects.requireNonNull(id, "id"),
        Objects.requireNonNull(fieldKey, "fieldKey"),
        Objects.requireNonNull(fieldType, "fieldType"),
        Objects.requireNonNull(fieldSource, "fieldSource"),
        textValue,
        numberValue,
        booleanValue,
        dateValue);
  }

  private static void requireCompatible(ContextFieldDefinition field, ContextFieldType... allowed) {
    Objects.requireNonNull(field, "field");
    for (ContextFieldType type : allowed) {
      if (field.type() == type) {
        return;
      }
    }
    throw new InvalidPublisherContextException();
  }

  public UUID id() {
    return id;
  }

  public String fieldKey() {
    return fieldKey;
  }

  public ContextFieldType fieldType() {
    return fieldType;
  }

  public ContextFieldSource fieldSource() {
    return fieldSource;
  }

  public String textValue() {
    return textValue;
  }

  public BigDecimal numberValue() {
    return numberValue;
  }

  public Boolean booleanValue() {
    return booleanValue;
  }

  public LocalDate dateValue() {
    return dateValue;
  }

  public Object publicValue() {
    return switch (fieldType) {
      case TEXT, ENUM -> textValue;
      case NUMBER -> numberValue;
      case BOOLEAN -> booleanValue;
      case DATE -> dateValue.toString();
    };
  }
}
