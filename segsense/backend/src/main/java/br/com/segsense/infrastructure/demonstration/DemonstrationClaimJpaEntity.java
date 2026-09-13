package br.com.segsense.infrastructure.demonstration;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "demonstration_claim", schema = "segsense")
public class DemonstrationClaimJpaEntity {

  @Id
  private UUID id;

  @Column(name = "story_id", nullable = false)
  private UUID storyId;

  @Column(name = "revision_number", nullable = false)
  private Integer revisionNumber;

  @Column(nullable = false)
  private Integer position;

  @Column(name = "claim_text", nullable = false)
  private String claimText;

  @Column(name = "source_id", nullable = false)
  private UUID sourceId;

  protected DemonstrationClaimJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getStoryId() {
    return storyId;
  }

  public void setStoryId(UUID storyId) {
    this.storyId = storyId;
  }

  public Integer getRevisionNumber() {
    return revisionNumber;
  }

  public void setRevisionNumber(Integer revisionNumber) {
    this.revisionNumber = revisionNumber;
  }

  public Integer getPosition() {
    return position;
  }

  public void setPosition(Integer position) {
    this.position = position;
  }

  public String getClaimText() {
    return claimText;
  }

  public void setClaimText(String claimText) {
    this.claimText = claimText;
  }

  public UUID getSourceId() {
    return sourceId;
  }

  public void setSourceId(UUID sourceId) {
    this.sourceId = sourceId;
  }
}
