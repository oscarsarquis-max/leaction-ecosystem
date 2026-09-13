package br.com.segsense.infrastructure.demonstration;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "demonstration_block", schema = "segsense")
public class DemonstrationBlockJpaEntity {

  @Id
  private UUID id;

  @Column(name = "story_id", nullable = false)
  private UUID storyId;

  @Column(name = "revision_number", nullable = false)
  private Integer revisionNumber;

  @Column(nullable = false)
  private Integer position;

  @Column(nullable = false, length = 200)
  private String title;

  @Column(nullable = false)
  private String body;

  protected DemonstrationBlockJpaEntity() {}

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

  public String getTitle() {
    return title;
  }

  public void setTitle(String title) {
    this.title = title;
  }

  public String getBody() {
    return body;
  }

  public void setBody(String body) {
    this.body = body;
  }
}
