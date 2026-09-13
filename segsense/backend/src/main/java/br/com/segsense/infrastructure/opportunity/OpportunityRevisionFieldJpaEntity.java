package br.com.segsense.infrastructure.opportunity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "contextual_opportunity_revision_field", schema = "segsense")
public class OpportunityRevisionFieldJpaEntity {

  @Id
  private UUID id;

  @Column(name = "opportunity_revision_id", nullable = false)
  private UUID opportunityRevisionId;

  @Column(name = "field_key", nullable = false, length = 40)
  private String fieldKey;

  @Column(nullable = false, length = 80)
  private String label;

  @Column(nullable = false, length = 16)
  private String type;

  @Column(nullable = false)
  private boolean required;

  @Column(nullable = false, length = 16)
  private String source;

  @Column(nullable = false, length = 16)
  private String classification;

  @Column(nullable = false)
  private int position;

  @JdbcTypeCode(SqlTypes.ARRAY)
  @Column(name = "allowed_values", columnDefinition = "text[]")
  private String[] allowedValues;

  protected OpportunityRevisionFieldJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
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

  public String getLabel() {
    return label;
  }

  public void setLabel(String label) {
    this.label = label;
  }

  public String getType() {
    return type;
  }

  public void setType(String type) {
    this.type = type;
  }

  public boolean isRequired() {
    return required;
  }

  public void setRequired(boolean required) {
    this.required = required;
  }

  public String getSource() {
    return source;
  }

  public void setSource(String source) {
    this.source = source;
  }

  public String getClassification() {
    return classification;
  }

  public void setClassification(String classification) {
    this.classification = classification;
  }

  public int getPosition() {
    return position;
  }

  public void setPosition(int position) {
    this.position = position;
  }

  public String[] getAllowedValues() {
    return allowedValues;
  }

  public void setAllowedValues(String[] allowedValues) {
    this.allowedValues = allowedValues;
  }
}
