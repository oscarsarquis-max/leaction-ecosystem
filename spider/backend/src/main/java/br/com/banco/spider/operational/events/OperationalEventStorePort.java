package br.com.banco.spider.operational.events;

import java.time.Instant;
import java.util.List;

public interface OperationalEventStorePort {
  void append(OperationalEvent event);

  List<OperationalEvent> findByExecutionId(String executionId);

  default List<OperationalEvent> findOccurredBetween(
      Instant fromInclusive, Instant toInclusive, int maxResults) {
    return List.of();
  }

  default List<OperationalEvent> findByExecutionId(
      String executionId, Instant from, Instant to) {
    return findByExecutionId(executionId).stream()
        .filter(event -> from == null || !event.occurredAt().isBefore(from))
        .filter(event -> to == null || !event.occurredAt().isAfter(to))
        .toList();
  }
}
