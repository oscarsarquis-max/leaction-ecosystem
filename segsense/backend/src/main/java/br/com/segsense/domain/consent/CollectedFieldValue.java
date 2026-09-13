package br.com.segsense.domain.consent;

import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.FieldClassification;
import br.com.segsense.domain.opportunity.OpportunityText;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.Objects;
import java.util.UUID;

public final class CollectedFieldValue {

  private static final BigDecimal MAX_ABS = new BigDecimal("1000000000000");

  private final UUID id;
  private final String fieldKey;
  private final ContextFieldType fieldType;
  private final ContextFieldSource fieldSource;
  private final FieldClassification classification;
  private final String textValue;
  private final BigDecimal numberValue;
  private final Boolean booleanValue;
  private final LocalDate dateValue;

  private CollectedFieldValue(
      UUID id,
      String fieldKey,
      ContextFieldType fieldType,
      ContextFieldSource fieldSource,
      FieldClassification classification,
      String textValue,
      BigDecimal numberValue,
      Boolean booleanValue,
      LocalDate dateValue) {
    this.id = id;
    this.fieldKey = fieldKey;
    this.fieldType = fieldType;
    this.fieldSource = fieldSource;
    this.classification = classification;
    this.textValue = textValue;
    this.numberValue = numberValue;
    this.booleanValue = booleanValue;
    this.dateValue = dateValue;
  }

  public static CollectedFieldValue parse(UUID id, ConsentNoticeField field, Object raw) {
    Objects.requireNonNull(field, "field");
    if (field.fieldSource() != ContextFieldSource.USER
        && field.fieldSource() != ContextFieldSource.EITHER) {
      throw new InvalidCollectedValueException();
    }
    if (field.classification() != FieldClassification.NON_PERSONAL) {
      throw new InvalidCollectedValueException();
    }
    if (raw == null || raw instanceof java.util.Map || raw instanceof java.util.Collection) {
      throw new InvalidCollectedValueException();
    }
    return switch (field.fieldType()) {
      case TEXT, ENUM -> text(id, field, raw);
      case NUMBER -> number(id, field, raw);
      case BOOLEAN -> bool(id, field, raw);
      case DATE -> date(id, field, raw);
    };
  }

  public static CollectedFieldValue restore(
      UUID id,
      String fieldKey,
      ContextFieldType fieldType,
      ContextFieldSource fieldSource,
      FieldClassification classification,
      String textValue,
      BigDecimal numberValue,
      Boolean booleanValue,
      LocalDate dateValue) {
    return new CollectedFieldValue(
        Objects.requireNonNull(id, "id"),
        Objects.requireNonNull(fieldKey, "fieldKey"),
        Objects.requireNonNull(fieldType, "fieldType"),
        Objects.requireNonNull(fieldSource, "fieldSource"),
        Objects.requireNonNull(classification, "classification"),
        textValue,
        numberValue,
        booleanValue,
        dateValue);
  }

  private static CollectedFieldValue text(UUID id, ConsentNoticeField field, Object raw) {
    if (!(raw instanceof String text)) {
      throw new InvalidCollectedValueException();
    }
    String value = OpportunityText.requiredLength(text, "O valor informado", 1, 200);
    OpportunityText.rejectPersonalIdentifier(value, "O valor informado");
    if (field.fieldType() == ContextFieldType.ENUM && !field.allowedValues().contains(value)) {
      throw new InvalidCollectedValueException();
    }
    return new CollectedFieldValue(
        id,
        field.fieldKey(),
        field.fieldType(),
        field.fieldSource(),
        FieldClassification.NON_PERSONAL,
        value,
        null,
        null,
        null);
  }

  private static CollectedFieldValue number(UUID id, ConsentNoticeField field, Object raw) {
    if (!(raw instanceof Number) && !(raw instanceof BigDecimal)) {
      throw new InvalidCollectedValueException();
    }
    BigDecimal value = raw instanceof BigDecimal decimal ? decimal : new BigDecimal(raw.toString());
    if (value.abs().compareTo(MAX_ABS) > 0 || value.scale() > 10) {
      throw new InvalidCollectedValueException();
    }
    BigDecimal canonical = value.stripTrailingZeros();
    if (canonical.scale() < 0) {
      canonical = canonical.setScale(0, RoundingMode.UNNECESSARY);
    }
    return new CollectedFieldValue(
        id,
        field.fieldKey(),
        ContextFieldType.NUMBER,
        field.fieldSource(),
        FieldClassification.NON_PERSONAL,
        null,
        canonical,
        null,
        null);
  }

  private static CollectedFieldValue bool(UUID id, ConsentNoticeField field, Object raw) {
    if (!(raw instanceof Boolean value)) {
      throw new InvalidCollectedValueException();
    }
    return new CollectedFieldValue(
        id,
        field.fieldKey(),
        ContextFieldType.BOOLEAN,
        field.fieldSource(),
        FieldClassification.NON_PERSONAL,
        null,
        null,
        value,
        null);
  }

  private static CollectedFieldValue date(UUID id, ConsentNoticeField field, Object raw) {
    if (!(raw instanceof String text)) {
      throw new InvalidCollectedValueException();
    }
    try {
      LocalDate parsed = LocalDate.parse(text, DateTimeFormatter.ISO_LOCAL_DATE);
      return new CollectedFieldValue(
          id,
          field.fieldKey(),
          ContextFieldType.DATE,
          field.fieldSource(),
          FieldClassification.NON_PERSONAL,
          null,
          null,
          null,
          parsed);
    } catch (DateTimeParseException exception) {
      throw new InvalidCollectedValueException();
    }
  }

  public Object publicValue() {
    return switch (fieldType) {
      case TEXT, ENUM -> textValue;
      case NUMBER -> numberValue;
      case BOOLEAN -> booleanValue;
      case DATE -> dateValue.toString();
    };
  }

  public String canonicalText() {
    Object value = publicValue();
    return value == null ? "" : String.valueOf(value);
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

  public FieldClassification classification() {
    return classification;
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
}
