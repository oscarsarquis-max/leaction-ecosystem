package br.com.banco.spider.infrastructure.persistence.memory;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventCategory;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Instant;
import java.util.Map;
import org.junit.jupiter.api.Test;

class InMemoryOperationalEventStoreTest {

  @Test
  void ordersByOccurredAtThenEventId() {
    InMemoryOperationalEventStore store = new InMemoryOperationalEventStore();
    store.append(event("event-b", "2026-08-25T10:00:01Z"));
    store.append(event("event-c", "2026-08-25T10:00:00Z"));
    store.append(event("event-a", "2026-08-25T10:00:01Z"));

    assertEquals(
        java.util.List.of("event-c", "event-a", "event-b"),
        store.findByExecutionId("exec-1").stream().map(OperationalEvent::eventId).toList());
  }

  private OperationalEvent event(String eventId, String occurredAt) {
    return new OperationalEvent(
        eventId,
        1,
        OperationalEventType.EXECUTION_STARTED,
        OperationalEventCategory.EXECUTION,
        Instant.parse(occurredAt),
        "exec-1",
        null,
        null,
        "test",
        OperationalEventOutcome.INFO,
        null,
        Map.of());
  }
}
