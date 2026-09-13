package br.com.segsense.domain.consent;

import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.opportunity.ContextFieldDefinition;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.FieldClassification;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

public final class ConsentNoticeField {

  private final UUID id;
  private final UUID opportunityRevisionId;
  private final String fieldKey;
  private final String label;
  private final ContextFieldType fieldType;
  private final ContextFieldSource fieldSource;
  private final FieldClassification classification;
  private final boolean required;
  private final int position;
  private final List<String> allowedValues;

  private ConsentNoticeField(
      UUID id,
      UUID opportunityRevisionId,
      String fieldKey,
      String label,
      ContextFieldType fieldType,
      ContextFieldSource fieldSource,
      FieldClassification classification,
      boolean required,
      int position,
      List<String> allowedValues) {
    this.id = id;
    this.opportunityRevisionId = opportunityRevisionId;
    this.fieldKey = fieldKey;
    this.label = label;
    this.fieldType = fieldType;
    this.fieldSource = fieldSource;
    this.classification = classification;
    this.required = required;
    this.position = position;
    this.allowedValues = allowedValues;
  }

  public static ConsentNoticeField fromDefinition(
      UUID id, UUID opportunityRevisionId, ContextFieldDefinition field) {
    Objects.requireNonNull(field, "field");
    if (field.source() != ContextFieldSource.USER && field.source() != ContextFieldSource.EITHER) {
      throw new CatalogValidationException(
          "O aviso de finalidade só pode cobrir campos do visitante ou compartilhados.");
    }
    if (field.classification() != FieldClassification.NON_PERSONAL) {
      throw new CatalogValidationException("A classificação do campo deve ser NON_PERSONAL.");
    }
    return new ConsentNoticeField(
        Objects.requireNonNull(id, "id"),
        Objects.requireNonNull(opportunityRevisionId, "opportunityRevisionId"),
        field.key(),
        field.label(),
        field.type(),
        field.source(),
        FieldClassification.NON_PERSONAL,
        field.required(),
        field.position(),
        field.allowedValues());
  }

  public static ConsentNoticeField restore(
      UUID id,
      UUID opportunityRevisionId,
      String fieldKey,
      String label,
      ContextFieldType fieldType,
      ContextFieldSource fieldSource,
      FieldClassification classification,
      boolean required,
      int position,
      List<String> allowedValues) {
    return new ConsentNoticeField(
        Objects.requireNonNull(id, "id"),
        Objects.requireNonNull(opportunityRevisionId, "opportunityRevisionId"),
        Objects.requireNonNull(fieldKey, "fieldKey"),
        Objects.requireNonNull(label, "label"),
        Objects.requireNonNull(fieldType, "fieldType"),
        Objects.requireNonNull(fieldSource, "fieldSource"),
        Objects.requireNonNull(classification, "classification"),
        required,
        position,
        allowedValues == null ? List.of() : List.copyOf(allowedValues));
  }

  public UUID id() {
    return id;
  }

  public UUID opportunityRevisionId() {
    return opportunityRevisionId;
  }

  public String fieldKey() {
    return fieldKey;
  }

  public String label() {
    return label;
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

  public boolean required() {
    return required;
  }

  public int position() {
    return position;
  }

  public List<String> allowedValues() {
    return allowedValues;
  }
}
