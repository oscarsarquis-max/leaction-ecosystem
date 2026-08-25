package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.OperationalEventEntity;
import java.time.Instant;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.domain.Pageable;

public interface OperationalEventJpaRepository
    extends JpaRepository<OperationalEventEntity, String> {

  List<OperationalEventEntity> findByExecutionIdOrderByOccurredAtAscEventIdAsc(
      String executionId);

  List<OperationalEventEntity>
      findByExecutionIdAndOccurredAtBetweenOrderByOccurredAtAscEventIdAsc(
          String executionId, Instant from, Instant to);

  List<OperationalEventEntity> findByOccurredAtBetweenOrderByOccurredAtAscEventIdAsc(
      Instant from, Instant to, Pageable pageable);
}
