package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.execution.callback.CallbackOutboxState;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.CallbackOutboxEntity;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CallbackOutboxJpaRepository extends JpaRepository<CallbackOutboxEntity, String> {

  Optional<CallbackOutboxEntity> findByLogicalCallbackId(String logicalCallbackId);

  Optional<CallbackOutboxEntity> findByExecutionId(String executionId);

  @Query(
      """
      select o from CallbackOutboxEntity o
      where o.state in :states and o.nextAttemptAt <= :now and o.expiresAt > :now
      order by o.nextAttemptAt
      """)
  List<CallbackOutboxEntity> findReady(
      @Param("states") List<CallbackOutboxState> states, @Param("now") Instant now);

  List<CallbackOutboxEntity> findByStateAndNextAttemptAtBefore(
      CallbackOutboxState state, Instant nextAttemptAt);
}
