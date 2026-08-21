package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_execution_plan")
@Getter
@Setter
@NoArgsConstructor
public class ExecutionPlanEntity {

  @Id
  @Column(name = "plan_id", length = 120)
  private String planId;

  @Column(name = "execution_id", nullable = false, unique = true, length = 120)
  private String executionId;

  @Column(name = "route_code", nullable = false, length = 120)
  private String routeCode;

  @Column(name = "route_version", nullable = false, length = 40)
  private String routeVersion;

  @Column(name = "journey_ref", nullable = false, length = 120)
  private String journeyRef;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "integrity_ref", nullable = false, length = 200)
  private String integrityRef;

  @Column(name = "schema_version", nullable = false, length = 20)
  private String schemaVersion;

  @Column(name = "canonical_plan_representation", nullable = false, columnDefinition = "text")
  private String canonicalPlanRepresentation;
}
