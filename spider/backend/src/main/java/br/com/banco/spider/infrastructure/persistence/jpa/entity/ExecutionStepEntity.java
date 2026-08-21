package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.step.StepState;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_execution_step")
@IdClass(ExecutionStepEntity.Pk.class)
@Getter
@Setter
@NoArgsConstructor
public class ExecutionStepEntity {

  @Id
  @Column(name = "execution_id", length = 120)
  private String executionId;

  @Id
  @Column(name = "step_id", length = 120)
  private String stepId;

  @Column(name = "ordered_position", nullable = false)
  private int orderedPosition;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private StepState state;

  @Column(name = "state_version", nullable = false)
  private long stateVersion;

  @Column(name = "active_attempt_id", length = 120)
  private String activeAttemptId;

  @Column(name = "output_result_ref", length = 120)
  private String outputResultRef;

  @Column(name = "terminal_error_code", length = 80)
  private String terminalErrorCode;

  @Column(name = "started_at")
  private Instant startedAt;

  @Column(name = "completed_at")
  private Instant completedAt;

  @Column(name = "last_updated_at", nullable = false)
  private Instant lastUpdatedAt;

  @Getter
  @Setter
  @NoArgsConstructor
  public static class Pk implements Serializable {
    private String executionId;
    private String stepId;

    public Pk(String executionId, String stepId) {
      this.executionId = executionId;
      this.stepId = stepId;
    }

    @Override
    public boolean equals(Object o) {
      if (this == o) return true;
      if (!(o instanceof Pk pk)) return false;
      return Objects.equals(executionId, pk.executionId) && Objects.equals(stepId, pk.stepId);
    }

    @Override
    public int hashCode() {
      return Objects.hash(executionId, stepId);
    }
  }
}
