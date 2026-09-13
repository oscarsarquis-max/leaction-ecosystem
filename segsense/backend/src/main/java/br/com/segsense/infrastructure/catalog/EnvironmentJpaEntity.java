package br.com.segsense.infrastructure.catalog;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "contextual_environment", schema = "segsense")
public class EnvironmentJpaEntity {

  @Id
  private UUID id;

  @Column(name = "publisher_id", nullable = false)
  private UUID publisherId;

  @Column(name = "channel_id", nullable = false)
  private UUID channelId;

  @Column(nullable = false, length = 50)
  private String key;

  @Column(nullable = false, length = 120)
  private String name;

  @Column(nullable = false, length = 32)
  private String type;

  @Column(name = "canonical_url", length = 2048)
  private String canonicalUrl;

  @Column(nullable = false, length = 16)
  private String status;

  @Version
  @Column(nullable = false)
  private Long version;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @Column(name = "created_by", nullable = false, length = 128)
  private String createdBy;

  @Column(name = "updated_by", nullable = false, length = 128)
  private String updatedBy;

  protected EnvironmentJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getPublisherId() {
    return publisherId;
  }

  public void setPublisherId(UUID publisherId) {
    this.publisherId = publisherId;
  }

  public UUID getChannelId() {
    return channelId;
  }

  public void setChannelId(UUID channelId) {
    this.channelId = channelId;
  }

  public String getKey() {
    return key;
  }

  public void setKey(String key) {
    this.key = key;
  }

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public String getType() {
    return type;
  }

  public void setType(String type) {
    this.type = type;
  }

  public String getCanonicalUrl() {
    return canonicalUrl;
  }

  public void setCanonicalUrl(String canonicalUrl) {
    this.canonicalUrl = canonicalUrl;
  }

  public String getStatus() {
    return status;
  }

  public void setStatus(String status) {
    this.status = status;
  }

  public Long getVersion() {
    return version;
  }

  public Instant getCreatedAt() {
    return createdAt;
  }

  public void setCreatedAt(Instant createdAt) {
    this.createdAt = createdAt;
  }

  public Instant getUpdatedAt() {
    return updatedAt;
  }

  public void setUpdatedAt(Instant updatedAt) {
    this.updatedAt = updatedAt;
  }

  public String getCreatedBy() {
    return createdBy;
  }

  public void setCreatedBy(String createdBy) {
    this.createdBy = createdBy;
  }

  public String getUpdatedBy() {
    return updatedBy;
  }

  public void setUpdatedBy(String updatedBy) {
    this.updatedBy = updatedBy;
  }
}
