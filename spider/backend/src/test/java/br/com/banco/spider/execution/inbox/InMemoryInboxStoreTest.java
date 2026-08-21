package br.com.banco.spider.execution.inbox;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.com.banco.spider.infrastructure.persistence.memory.InMemoryInboxStore;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class InMemoryInboxStoreTest {

  @Test
  void reserveDuplicateAndConflict() {
    InMemoryInboxStore store = new InMemoryInboxStore();
    Instant now = Instant.parse("2026-01-01T00:00:00Z");
    InboxRecord a =
        new InboxRecord(
            "m1",
            "source:a",
            "binding:x",
            "contract:c",
            "dedup",
            "fp1",
            "1.0",
            "e1",
            "s1",
            null,
            now,
            InboxValidationState.RECEIVED,
            InboxProcessingState.PENDING,
            null,
            null,
            now.plusSeconds(60));
    assertEquals(InboxReservationStatus.RESERVED_NEW, store.reserve(a).status());
    assertEquals(InboxReservationStatus.DUPLICATE_SAME_SIGNAL, store.reserve(a).status());

    InboxRecord conflict =
        new InboxRecord(
            "m1",
            "source:a",
            "binding:x",
            "contract:c",
            "dedup",
            "fp2",
            "1.0",
            "e1",
            "s1",
            null,
            now,
            InboxValidationState.RECEIVED,
            InboxProcessingState.PENDING,
            null,
            null,
            now.plusSeconds(60));
    assertEquals(InboxReservationStatus.CONFLICTING_SIGNAL, store.reserve(conflict).status());
  }
}
