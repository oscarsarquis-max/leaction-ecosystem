package br.com.banco.spider.operational.events;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.readmodel.OperationalRedactionService;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;
import org.junit.jupiter.api.Test;

class OperationalEventPublisherTest {

  private final Instant now = Instant.parse("2026-08-25T10:00:00Z");

  @Test
  void createsSanitizedImmutableEvent() {
    List<OperationalEvent> stored = new CopyOnWriteArrayList<>();
    SafeOperationalEventPublisher publisher =
        new SafeOperationalEventPublisher(
            IdentifierGenerator.sequential("test"),
            SpiderClock.fixed(now),
            store(stored::add),
            new OperationalRedactionService());

    publisher.publish(
        draft(
            OperationalEventAttributes.builder()
                .reasonCode("OK")
                .put("password", "must-not-leak")
                .component("x".repeat(250))
                .build()));

    assertEquals(1, stored.size());
    OperationalEvent event = stored.getFirst();
    assertEquals(1, event.schemaVersion());
    assertEquals(OperationalEventCategory.EXECUTION, event.category());
    assertEquals(200, event.metadata().get("component").length());
    assertFalse(event.metadata().containsKey("password"));
    assertDoesNotThrow(() -> event.metadata().forEach((key, value) -> {}));
  }

  @Test
  void storeFailureIsFailOpen() {
    SafeOperationalEventPublisher publisher =
        new SafeOperationalEventPublisher(
            IdentifierGenerator.sequential("test"),
            SpiderClock.fixed(now),
            store(event -> {
                  throw new IllegalStateException("store unavailable");
                }),
            new OperationalRedactionService());

    assertDoesNotThrow(() -> publisher.publish(draft(OperationalEventAttributes.empty())));
  }

  @Test
  void recursionGuardDropsNestedPublish() {
    AtomicReference<SafeOperationalEventPublisher> publisherRef = new AtomicReference<>();
    List<OperationalEvent> stored = new CopyOnWriteArrayList<>();
    OperationalEventStorePort recursiveStore =
        store(event -> {
          stored.add(event);
          publisherRef.get().publish(draft(OperationalEventAttributes.empty()));
        });
    SafeOperationalEventPublisher publisher =
        new SafeOperationalEventPublisher(
            IdentifierGenerator.sequential("test"),
            SpiderClock.fixed(now),
            recursiveStore,
            new OperationalRedactionService());
    publisherRef.set(publisher);

    publisher.publish(draft(OperationalEventAttributes.empty()));

    assertEquals(1, stored.size());
  }

  private OperationalEventDraft draft(OperationalEventAttributes attributes) {
    return OperationalEventDraft.builder()
        .eventType(OperationalEventType.EXECUTION_STARTED)
        .executionId("exec-1")
        .correlationId("corr-1")
        .source("test")
        .outcome(OperationalEventOutcome.INFO)
        .attributes(attributes)
        .build();
  }

  private static OperationalEventStorePort store(Consumer<OperationalEvent> appender) {
    return new OperationalEventStorePort() {
      @Override
      public void append(OperationalEvent event) {
        appender.accept(event);
      }

      @Override
      public List<OperationalEvent> findByExecutionId(String executionId) {
        return List.of();
      }
    };
  }
}
