package br.com.banco.spider.security.replay;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.infrastructure.persistence.memory.InMemoryReplayGuardAdapter;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class ReplayGuardTest {

  private static final Instant NOW = Instant.parse("2026-08-21T19:00:00Z");

  @Test
  void reserveDuplicateAndConflict() {
    InMemoryReplayGuardAdapter guard = new InMemoryReplayGuardAdapter();
    ReplayReservation first =
        new ReplayReservation(
            "r1",
            "scope1",
            "nonce1",
            "fp-a",
            "v1",
            "key:x",
            "v1",
            "profile@1",
            NOW,
            NOW.plusSeconds(60),
            ReplayDecisionStatus.RESERVED,
            0L);
    assertEquals(ReplayDecisionStatus.RESERVED, guard.reserve(first).status());

    ReplayReservation same =
        new ReplayReservation(
            "r2",
            "scope1",
            "nonce1",
            "fp-a",
            "v1",
            "key:x",
            "v1",
            "profile@1",
            NOW,
            NOW.plusSeconds(60),
            ReplayDecisionStatus.RESERVED,
            0L);
    assertEquals(ReplayDecisionStatus.DUPLICATE_SAME_MESSAGE, guard.reserve(same).status());

    ReplayReservation conflict =
        new ReplayReservation(
            "r3",
            "scope1",
            "nonce1",
            "fp-b",
            "v1",
            "key:x",
            "v1",
            "profile@1",
            NOW,
            NOW.plusSeconds(60),
            ReplayDecisionStatus.RESERVED,
            0L);
    assertEquals(ReplayDecisionStatus.REPLAY_CONFLICT, guard.reserve(conflict).status());
  }

  @Test
  void concurrentReserveOneWins() {
    InMemoryReplayGuardAdapter guard = new InMemoryReplayGuardAdapter();
    ReplayReservation a =
        new ReplayReservation(
            "ra", "s", "n", "fp", "v1", null, null, null, NOW, NOW.plusSeconds(30),
            ReplayDecisionStatus.RESERVED, 0L);
    ReplayReservation b =
        new ReplayReservation(
            "rb", "s", "n", "fp", "v1", null, null, null, NOW, NOW.plusSeconds(30),
            ReplayDecisionStatus.RESERVED, 0L);
    ReplayDecision d1 = guard.reserve(a);
    ReplayDecision d2 = guard.reserve(b);
    assertEquals(ReplayDecisionStatus.RESERVED, d1.status());
    assertEquals(ReplayDecisionStatus.DUPLICATE_SAME_MESSAGE, d2.status());
  }

  @Test
  void cleanupRemovesExpired() {
    InMemoryReplayGuardAdapter guard = new InMemoryReplayGuardAdapter();
    guard.reserve(
        new ReplayReservation(
            "r", "s", "n", "fp", "v1", null, null, null, NOW, NOW.plusSeconds(1),
            ReplayDecisionStatus.RESERVED, 0L));
    assertEquals(1, guard.size());
    int removed = guard.cleanupExpired(NOW.plusSeconds(2), 10);
    assertEquals(1, removed);
    assertEquals(0, guard.size());
  }

  @Test
  void expiredProofNotReservedAsValid() {
    InMemoryReplayGuardAdapter guard = new InMemoryReplayGuardAdapter();
    ReplayDecision d =
        guard.reserve(
            new ReplayReservation(
                "r", "s", "n", "fp", "v1", null, null, null, NOW, NOW,
                ReplayDecisionStatus.RESERVED, 0L));
    assertEquals(ReplayDecisionStatus.EXPIRED_PROOF, d.status());
  }
}
