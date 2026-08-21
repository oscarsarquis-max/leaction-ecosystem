package br.com.banco.spider.execution.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionTransitionRecord;
import br.com.banco.spider.execution.persistence.support.InMemoryPersistenceBundle;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class InMemoryPersistenceStoreTest {

  @Test
  void stateVersionOptimisticLockAndAppendOnlyTransitions() {
    var bundle =
        new InMemoryPersistenceBundle(
            SpiderClock.fixed(Instant.parse("2026-01-01T00:00:00Z")),
            IdentifierGenerator.sequential("p"));
    var req = CanonicalRouteFixtures.request("e1", null);
    bundle.coordinator.createExecutionOnly(req);
    ExecutionControlRecord c1 =
        bundle.coordinator.transition(
            "e1",
            ExecutionState.RECEIVED,
            0,
            ExecutionState.VALIDATED,
            "V",
            null,
            null,
            null,
            null,
            null);
    assertEquals(1, c1.stateVersion());
    assertThrows(
        InMemoryExecutionControlStore.OptimisticLockException.class,
        () ->
            bundle.coordinator.transition(
                "e1",
                ExecutionState.RECEIVED,
                0,
                ExecutionState.REJECTED,
                "bad",
                null,
                null,
                null,
                null,
                null));
    assertEquals(2, bundle.transitionStore.findByExecutionId("e1").size());
    assertThrows(
        IllegalStateException.class,
        () ->
            bundle.transitionStore.append(
                new ExecutionTransitionRecord(
                    "dup",
                    "e1",
                    1,
                    null,
                    ExecutionState.RECEIVED,
                    "X",
                    Instant.parse("2026-01-01T00:00:00Z"),
                    null)));
  }

  @Test
  void enumsPersistedAsNamesViaModels() {
    var bundle =
        new InMemoryPersistenceBundle(
            SpiderClock.fixed(Instant.parse("2026-01-01T00:00:00Z")),
            IdentifierGenerator.sequential("p"));
    bundle.coordinator.createExecutionOnly(CanonicalRouteFixtures.request("e2", null));
    assertEquals(
        ExecutionState.RECEIVED,
        bundle.controlStore.findByExecutionId("e2").orElseThrow().state());
    assertTrue(
        bundle.transitionStore.findByExecutionId("e2").stream()
            .allMatch(t -> t.newState().name().equals("RECEIVED")));
  }
}
