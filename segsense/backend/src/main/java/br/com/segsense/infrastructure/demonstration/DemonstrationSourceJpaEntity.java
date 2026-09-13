package br.com.segsense.infrastructure.demonstration;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "demonstration_source", schema = "segsense")
public class DemonstrationSourceJpaEntity {

  @Id
  private UUID id;

  @Column(name = "source_key", nullable = false, unique = true, length = 50)
  private String sourceKey;

  @Column(nullable = false)
  private String url;

  @Column(name = "consulted_on", nullable = false)
  private LocalDate consultedOn;

  @Column(name = "access_kind", nullable = false, length = 32)
  private String accessKind;

  @Column(name = "verification_status", nullable = false, length = 32)
  private String verificationStatus;

  @Column(nullable = false, length = 500)
  private String summary;

  protected DemonstrationSourceJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public String getSourceKey() {
    return sourceKey;
  }

  public String getUrl() {
    return url;
  }

  public LocalDate getConsultedOn() {
    return consultedOn;
  }

  public String getAccessKind() {
    return accessKind;
  }

  public String getVerificationStatus() {
    return verificationStatus;
  }

  public String getSummary() {
    return summary;
  }
}
