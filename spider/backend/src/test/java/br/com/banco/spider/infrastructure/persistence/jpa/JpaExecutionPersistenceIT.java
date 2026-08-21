package br.com.banco.spider.infrastructure.persistence.jpa;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionControlEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionStepEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionControlJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionStepJpaRepository;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.test.context.TestPropertySource;

/**
 * Cobertura JPA real mínima (H2). Schema via hibernate ddl-auto=create-drop
 * alinhado às entidades; migrations SQL permanecem a fonte para PostgreSQL.
 */
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.ANY)
@EntityScan({"br.com.banco.spider.infrastructure.persistence.jpa.entity", "br.com.banco.spider.model"})
@EnableJpaRepositories({"br.com.banco.spider.infrastructure.persistence.jpa.repository", "br.com.banco.spider.repository"})
@TestPropertySource(
    properties = {
      "spring.datasource.url=jdbc:h2:mem:spider_jpa;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class JpaExecutionPersistenceIT {

  @Autowired ExecutionControlJpaRepository controlRepo;
  @Autowired ExecutionStepJpaRepository stepRepo;

  @Test
  void persistsControlAndStepWithStringEnums() {
    Instant now = Instant.parse("2026-07-21T12:00:00Z");
    ExecutionControlEntity c = new ExecutionControlEntity();
    c.setExecutionId("e-jpa-1");
    c.setContextId("ctx");
    c.setCorrelationId("corr");
    c.setState(ExecutionState.PLANNED);
    c.setStateVersion(1L);
    c.setLastUpdatedAt(now);
    c.setRetentionClassRef("retention:technical-default@1");
    controlRepo.save(c);

    ExecutionStepEntity s = new ExecutionStepEntity();
    s.setExecutionId("e-jpa-1");
    s.setStepId("step-1");
    s.setOrderedPosition(0);
    s.setState(StepState.READY);
    s.setStateVersion(0L);
    s.setLastUpdatedAt(now);
    stepRepo.save(s);

    assertTrue(controlRepo.findById("e-jpa-1").isPresent());
    assertEquals(ExecutionState.PLANNED, controlRepo.findById("e-jpa-1").orElseThrow().getState());
    assertEquals(StepState.READY, stepRepo.findById(new ExecutionStepEntity.Pk("e-jpa-1", "step-1")).orElseThrow().getState());
  }
}
