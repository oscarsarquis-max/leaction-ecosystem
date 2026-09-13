package br.com.segsense.infrastructure.link;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;
import org.hibernate.annotations.Immutable;

@Entity
@Immutable
@Table(name = "published_context_link_binding", schema = "segsense")
public class PublishedContextLinkBindingJpaEntity {

  @Id private UUID id;

  @Column(name = "link_id", nullable = false)
  private UUID linkId;

  @Column(name = "opportunity_revision_id", nullable = false)
  private UUID opportunityRevisionId;

  @Column(name = "field_key", nullable = false, length = 40)
  private String fieldKey;

  @Column(name = "field_type", nullable = false, length = 16)
  private String fieldType;

  @Column(name = "field_source", nullable = false, length = 16)
  private String fieldSource;

  @Column(name = "text_value", length = 200)
  private String textValue;

  @Column(name = "number_value")
  private BigDecimal numberValue;

  @Column(name = "boolean_value")
  private Boolean booleanValue;

  @Column(name = "date_value")
  private LocalDate dateValue;

  protected PublishedContextLinkBindingJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getLinkId() {
    return linkId;
  }

  public void setLinkId(UUID linkId) {
    this.linkId = linkId;
  }

  public UUID getOpportunityRevisionId() {
    return opportunityRevisionId;
  }

  public void setOpportunityRevisionId(UUID opportunityRevisionId) {
    this.opportunityRevisionId = opportunityRevisionId;
  }

  public String getFieldKey() {
    return fieldKey;
  }

  public void setFieldKey(String fieldKey) {
    this.fieldKey = fieldKey;
  }

  public String getFieldType() {
    return fieldType;
  }

  public void setFieldType(String fieldType) {
    this.fieldType = fieldType;
  }

  public String getFieldSource() {
    return fieldSource;
  }

  public void setFieldSource(String fieldSource) {
    this.fieldSource = fieldSource;
  }

  public String getTextValue() {
    return textValue;
  }

  public void setTextValue(String textValue) {
    this.textValue = textValue;
  }

  public BigDecimal getNumberValue() {
    return numberValue;
  }

  public void setNumberValue(BigDecimal numberValue) {
    this.numberValue = numberValue;
  }

  public Boolean getBooleanValue() {
    return booleanValue;
  }

  public void setBooleanValue(Boolean booleanValue) {
    this.booleanValue = booleanValue;
  }

  public LocalDate getDateValue() {
    return dateValue;
  }

  public void setDateValue(LocalDate dateValue) {
    this.dateValue = dateValue;
  }
}
