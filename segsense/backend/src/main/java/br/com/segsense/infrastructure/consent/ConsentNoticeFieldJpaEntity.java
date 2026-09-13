package br.com.segsense.infrastructure.consent;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "consent_notice_field", schema = "segsense")
public class ConsentNoticeFieldJpaEntity {

  @Id private UUID id;

  @Column(name = "snapshot_id", nullable = false)
  private UUID snapshotId;

  @Column(name = "opportunity_revision_id", nullable = false)
  private UUID opportunityRevisionId;

  @Column(name = "field_key", nullable = false, length = 40)
  private String fieldKey;

  @Column(name = "field_label", nullable = false, length = 80)
  private String fieldLabel;

  @Column(name = "field_type", nullable = false, length = 16)
  private String fieldType;

  @Column(name = "field_source", nullable = false, length = 16)
  private String fieldSource;

  @Column(nullable = false, length = 16)
  private String classification;

  @Column(nullable = false)
  private boolean required;

  @Column(nullable = false)
  private int position;

  @JdbcTypeCode(SqlTypes.ARRAY)
  @Column(name = "allowed_values", columnDefinition = "text[]")
  private String[] allowedValues;

  protected ConsentNoticeFieldJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getSnapshotId() {
    return snapshotId;
  }

  public void setSnapshotId(UUID snapshotId) {
    this.snapshotId = snapshotId;
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

  public String getFieldLabel() {
    return fieldLabel;
  }

  public void setFieldLabel(String fieldLabel) {
    this.fieldLabel = fieldLabel;
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

  public String getClassification() {
    return classification;
  }

  public void setClassification(String classification) {
    this.classification = classification;
  }

  public boolean isRequired() {
    return required;
  }

  public void setRequired(boolean required) {
    this.required = required;
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
