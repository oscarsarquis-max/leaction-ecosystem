package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

public class InMemoryOperationalEventStore implements OperationalEventStorePort {

  private static final Comparator<OperationalEvent> ORDER =
      Comparator.comparing(OperationalEvent::occurredAt).thenComparing(OperationalEvent::eventId);

  private final Map<String, CopyOnWriteArrayList<OperationalEvent>> byExecutionId =
      new ConcurrentHashMap<>();

  @Override
  public void append(OperationalEvent event) {
    byExecutionId
        .computeIfAbsent(event.executionId(), ignored -> new CopyOnWriteArrayList<>())
        .add(event);
  }

  @Override
  public List<OperationalEvent> findByExecutionId(String executionId) {
    if (executionId == null || executionId.isBlank()) {
      return List.of();
    }
    return byExecutionId.getOrDefault(executionId, new CopyOnWriteArrayList<>()).stream()
        .sorted(ORDER)
        .toList();
  }

  @Override
  public List<OperationalEvent> findOccurredBetween(
      Instant fromInclusive, Instant toInclusive, int maxResults) {
    return byExecutionId.values().stream()
        .flatMap(List::stream)
        .filter(event -> !event.occurredAt().isBefore(fromInclusive))
        .filter(event -> !event.occurredAt().isAfter(toInclusive))
        .sorted(ORDER)
        .limit(Math.max(0, maxResults))
        .toList();
  }

  public void clear() {
    byExecutionId.clear();
  }
}
