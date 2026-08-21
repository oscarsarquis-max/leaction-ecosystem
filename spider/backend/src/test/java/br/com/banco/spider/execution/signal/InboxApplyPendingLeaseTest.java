package br.com.banco.spider.execution.signal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.inbox.InboxReservationStatus;
import br.com.banco.spider.execution.inbox.InboxValidationState;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryInboxStore;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class InboxApplyPendingLeaseTest {

  @Test
  void claimLeaseIsExclusiveAndIdempotentDuplicate() {
    InMemoryInboxStore store = new InMemoryInboxStore();
    Instant now = Instant.parse("2026-08-21T20:00:00Z");
    InboxRecord candidate =
        new InboxRecord(
            "m1",
            "src",
            "binding",
            "contract",
            "dedup",
            "fp",
            "v1",
            "exec",
            "step",
            null,
            now,
            InboxValidationState.VALIDATED,
            InboxProcessingState.APPLY_PENDING,
            "env:1",
            null,
            now.plusSeconds(3600),
            "wait-1",
            "signal:x@1",
            "fp",
            0,
            now,
            null,
            null,
            0L,
            now,
            null);
    assertEquals(InboxReservationStatus.RESERVED_NEW, store.reserve(candidate).status());
    assertTrue(
        store
            .claimForApplication("src", "m1", 0L, "w1", now.plusSeconds(30), now)
            .isPresent());
    assertTrue(
        store
            .claimForApplication("src", "m1", 0L, "w2", now.plusSeconds(30), now)
            .isEmpty());
    assertEquals(
        InboxReservationStatus.EXISTING_IN_PROGRESS, store.reserve(candidate).status());
  }
}
