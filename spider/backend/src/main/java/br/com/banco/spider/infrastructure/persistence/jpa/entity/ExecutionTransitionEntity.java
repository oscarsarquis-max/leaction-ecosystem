package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.domain.ExecutionState;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(
    name = "tb_execution_transition",
    uniqueConstraints =
        @UniqueConstraint(name = "uq_tb_execution_transition_seq", columnNames = {"execution_id", "sequence_no"}))
@Getter
@Setter
@NoArgsConstructor
public class ExecutionTransitionEntity {

  @Id
  @Column(name = "transition_id", length = 120)
  private String transitionId;

  @Column(name = "execution_id", nullable = false, length = 120)
  private String executionId;

  @Column(name = "sequence_no", nullable = false)
  private long sequenceNo;

  @Enumerated(EnumType.STRING)
  @Column(name = "previous_state", length = 40)
  private ExecutionState previousState;

  @Enumerated(EnumType.STRING)
  @Column(name = "new_state", nullable = false, length = 40)
  private ExecutionState newState;

  @Column(name = "reason_code", nullable = false, length = 80)
  private String reasonCode;

  @Column(name = "occurred_at", nullable = false)
  private Instant occurredAt;

  @Column(name = "attempt_id", length = 120)
  private String attemptId;
}
