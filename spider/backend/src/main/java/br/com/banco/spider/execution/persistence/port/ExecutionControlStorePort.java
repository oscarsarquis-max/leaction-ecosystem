package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import java.util.List;
import java.util.Optional;

/** Porta de controle de execução — sem JPA. */
public interface ExecutionControlStorePort {
  void insert(ExecutionControlRecord record);

  Optional<ExecutionControlRecord> findByExecutionId(String executionId);

  ExecutionControlRecord updateState(
      String executionId,
      ExecutionState expectedState,
      long expectedVersion,
      ExecutionState newState,
      br.com.banco.spider.execution.domain.TechnicalStatus technicalStatus,
      String planId,
      String routeCode,
      String routeVersion,
      String activeWaitType,
      java.time.Instant startedAt,
      java.time.Instant completedAt,
      java.time.Instant lastUpdatedAt);

  List<ExecutionControlRecord> findByStates(List<ExecutionState> states);

  /**
   * Lista recentes ordenada por startedAt desc, executionId desc. Cursor: registros estritamente
   * anteriores a (cursorStartedAt, cursorExecutionId).
   */
  List<ExecutionControlRecord> listRecent(
      int limit, java.time.Instant cursorStartedAt, String cursorExecutionId);
}
