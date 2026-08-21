package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_execution_result")
@Getter
@Setter
@NoArgsConstructor
public class ExecutionResultEntity {

  @Id
  @Column(name = "result_ref", length = 120)
  private String resultRef;

  @Column(name = "execution_id", nullable = false, unique = true, length = 120)
  private String executionId;

  @Column(name = "contract_version", nullable = false, length = 40)
  private String contractVersion;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private ExecutionState state;

  @Enumerated(EnumType.STRING)
  @Column(name = "technical_status", nullable = false, length = 40)
  private TechnicalStatus technicalStatus;

  @Column(name = "result_representation", nullable = false, columnDefinition = "text")
  private String resultRepresentation;

  @Column(name = "content_digest", nullable = false, length = 200)
  private String contentDigest;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;
}
