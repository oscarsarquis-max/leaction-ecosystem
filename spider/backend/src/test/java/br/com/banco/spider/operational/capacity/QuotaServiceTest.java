package br.com.banco.spider.operational.capacity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Duration;
import org.junit.jupiter.api.Test;

/** Bordas da janela de quota: o consumo e a leitura enxergam sempre a mesma fronteira. */
class QuotaServiceTest {

  private static final String SCOPE = "schedule:sched:test@1";
  private static final Duration WINDOW = CapacityTestSupport.WINDOW;

  private final CapacityTestSupport.MutableClock clock =
      new CapacityTestSupport.MutableClock(CapacityTestSupport.T0);
  private final QuotaService quotas = new QuotaService(clock);

  @Test
  void consumesUpToTheQuotaAndRefusesTheNext() {
    assertTrue(quotas.tryConsume(SCOPE, 2, WINDOW));
    assertTrue(quotas.tryConsume(SCOPE, 2, WINDOW));

    assertFalse(quotas.tryConsume(SCOPE, 2, WINDOW));
    assertEquals(2, quotas.used(SCOPE, WINDOW));
  }

  @Test
  void quotaThatIsNotDeclaredNeverLimits() {
    assertTrue(quotas.tryConsume(SCOPE, 0, WINDOW));
    assertTrue(quotas.tryConsume(SCOPE, -5, WINDOW));
    assertTrue(quotas.tryConsume(null, 1, WINDOW));
    assertTrue(quotas.tryConsume(SCOPE, 1, null));

    assertEquals(0, quotas.used(SCOPE, WINDOW));
    assertNull(quotas.windowStartedAt(SCOPE));
  }

  @Test
  void theLastInstantOfTheWindowStillBelongsToIt() {
    assertTrue(quotas.tryConsume(SCOPE, 1, WINDOW));

    clock.advance(WINDOW.minusMillis(1));

    assertFalse(quotas.tryConsume(SCOPE, 1, WINDOW), "a janela só vira quando ela termina");
    assertEquals(1, quotas.used(SCOPE, WINDOW));
  }

  @Test
  void exactlyAtTheWindowEndTheCountRestarts() {
    assertTrue(quotas.tryConsume(SCOPE, 1, WINDOW));

    clock.advance(WINDOW);

    assertTrue(quotas.tryConsume(SCOPE, 1, WINDOW));
    assertEquals(1, quotas.used(SCOPE, WINDOW));
    assertEquals(CapacityTestSupport.T0.plus(WINDOW), quotas.windowStartedAt(SCOPE));
  }

  @Test
  void windowStartIsAnchoredOnTheFirstConsumptionNotOnTheClockOrigin() {
    clock.advance(Duration.ofSeconds(17));
    assertTrue(quotas.tryConsume(SCOPE, 1, WINDOW));

    assertEquals(CapacityTestSupport.T0.plusSeconds(17), quotas.windowStartedAt(SCOPE));

    clock.advance(WINDOW.minusSeconds(1));
    assertFalse(quotas.tryConsume(SCOPE, 1, WINDOW));
    clock.advance(Duration.ofSeconds(1));
    assertTrue(quotas.tryConsume(SCOPE, 1, WINDOW));
  }

  @Test
  void readingAloneRollsTheExpiredWindowWithoutConsuming() {
    assertTrue(quotas.tryConsume(SCOPE, 1, WINDOW));
    clock.advance(WINDOW);

    assertEquals(0, quotas.used(SCOPE, WINDOW));
    assertTrue(quotas.tryConsume(SCOPE, 1, WINDOW), "a leitura não pode consumir a nova janela");
  }

  @Test
  void scopesKeepIndependentWindows() {
    String other = "schedule:sched:other@1";
    assertTrue(quotas.tryConsume(SCOPE, 1, WINDOW));

    assertFalse(quotas.tryConsume(SCOPE, 1, WINDOW));
    assertTrue(quotas.tryConsume(other, 1, WINDOW));
    assertEquals(1, quotas.used(other, WINDOW));
  }

  @Test
  void unknownScopeReportsNoUsage() {
    assertEquals(0, quotas.used("schedule:never-seen@1", WINDOW));
    assertEquals(0, quotas.used(null, WINDOW));
    assertNull(quotas.windowStartedAt("schedule:never-seen@1"));
  }
}
