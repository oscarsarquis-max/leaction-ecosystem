package br.com.banco.spider.operational.events;

import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.readmodel.OperationalRedactionService;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class SafeOperationalEventPublisher implements OperationalEventPublisher {

  private static final Logger log = LoggerFactory.getLogger(SafeOperationalEventPublisher.class);
  private static final ThreadLocal<Boolean> PUBLISHING = ThreadLocal.withInitial(() -> false);

  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final OperationalEventStorePort store;
  private final OperationalRedactionService redaction;

  public SafeOperationalEventPublisher(
      IdentifierGenerator ids,
      SpiderClock clock,
      OperationalEventStorePort store,
      OperationalRedactionService redaction) {
    this.ids = ids;
    this.clock = clock;
    this.store = store;
    this.redaction = redaction;
  }

  @Override
  public void publish(OperationalEventDraft draft) {
    if (Boolean.TRUE.equals(PUBLISHING.get())) {
      return;
    }
    PUBLISHING.set(true);
    try {
      Map<String, Object> raw = new LinkedHashMap<>();
      draft.attributes().toMap().forEach(raw::put);
      Map<String, Object> cleaned = redaction.redact(raw, 2, 200).projection();
      Map<String, String> metadata = new LinkedHashMap<>();
      cleaned.forEach((key, value) -> metadata.put(key, value == null ? "" : String.valueOf(value)));
      store.append(
          new OperationalEvent(
              ids.nextId("oev"),
              1,
              draft.eventType(),
              draft.eventType().category(),
              clock.now(),
              draft.executionId(),
              draft.interactionId(),
              draft.correlationId(),
              draft.source(),
              draft.outcome(),
              draft.durationMs(),
              metadata));
    } catch (Throwable failure) {
      log.warn(
          "event=telemetry_publish_failed reasonCode={}",
          failure.getClass().getSimpleName());
    } finally {
      PUBLISHING.remove();
    }
  }
}
