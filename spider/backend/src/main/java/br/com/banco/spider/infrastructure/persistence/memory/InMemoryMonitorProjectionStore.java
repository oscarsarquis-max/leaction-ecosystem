package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.operational.monitor.MonitorProjectionMerge;
import br.com.banco.spider.operational.monitor.MonitorProjectionPort;
import br.com.banco.spider.operational.monitor.MonitorProjectionRecord;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

public class InMemoryMonitorProjectionStore implements MonitorProjectionPort {

  private static final Comparator<MonitorProjectionRecord> ORDER =
      Comparator.comparing(MonitorProjectionRecord::updatedAt, Comparator.nullsLast(Comparator.reverseOrder()))
          .thenComparing(MonitorProjectionRecord::recordId, Comparator.nullsLast(Comparator.reverseOrder()));

  private final ConcurrentHashMap<String, MonitorProjectionRecord> byId = new ConcurrentHashMap<>();

  @Override
  public void upsert(MonitorProjectionRecord record) {
    if (record == null || record.recordId() == null || record.recordId().isBlank()) {
      return;
    }
    byId.compute(record.recordId(), (key, current) -> MonitorProjectionMerge.apply(current, record));
  }

  @Override
  public Optional<MonitorProjectionRecord> findById(String recordId) {
    if (recordId == null || recordId.isBlank()) {
      return Optional.empty();
    }
    return Optional.ofNullable(byId.get(recordId)).filter(item -> !expired(item, Instant.now()));
  }

  @Override
  public List<MonitorProjectionRecord> search(
      String query,
      String origin,
      String kind,
      Instant now,
      int limit,
      Instant cursorUpdatedAt,
      String cursorId) {
    Instant clock = now == null ? Instant.now() : now;
    String q = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
    return byId.values().stream()
        .filter(item -> !expired(item, clock))
        .filter(item -> kind == null || kind.isBlank() || kind.equals(item.kind()))
        .filter(
            item ->
                origin == null
                    || origin.isBlank()
                    || origin.equalsIgnoreCase(item.origin())
                    || origin.equalsIgnoreCase(item.satelliteId()))
        .filter(item -> q.isEmpty() || matches(item, q))
        .filter(item -> afterCursor(item, cursorUpdatedAt, cursorId))
        .sorted(ORDER)
        .limit(Math.max(0, limit))
        .toList();
  }

  @Override
  public int purgeExpired(Instant now) {
    Instant clock = now == null ? Instant.now() : now;
    AtomicInteger removed = new AtomicInteger();
    byId.entrySet().removeIf(
        entry -> {
          if (expired(entry.getValue(), clock)) {
            removed.incrementAndGet();
            return true;
          }
          return false;
        });
    return removed.get();
  }

  public void clear() {
    byId.clear();
  }

  private static boolean expired(MonitorProjectionRecord item, Instant now) {
    return item.retentionUntil() != null && !item.retentionUntil().isAfter(now);
  }

  private static boolean matches(MonitorProjectionRecord item, String q) {
    return contains(item.recordId(), q)
        || contains(item.messageId(), q)
        || contains(item.correlationId(), q)
        || contains(item.satelliteId(), q)
        || contains(item.origin(), q)
        || contains(item.companyId(), q)
        || contains(item.externalRef(), q)
        || contains(item.objective(), q)
        || contains(item.eventKey(), q)
        || contains(item.capability(), q)
        || contains(item.syncRunId(), q)
        || contains(item.relatedSyncId(), q)
        || contains(item.relatedPaymentId(), q)
        || contains(item.kind(), q);
  }

  private static boolean contains(String value, String q) {
    return value != null && value.toLowerCase(Locale.ROOT).contains(q);
  }

  private static boolean afterCursor(MonitorProjectionRecord item, Instant cursorUpdatedAt, String cursorId) {
    if (cursorUpdatedAt == null) {
      return true;
    }
    if (item.updatedAt() == null) {
      return false;
    }
    int compared = item.updatedAt().compareTo(cursorUpdatedAt);
    if (compared < 0) {
      return true;
    }
    if (compared > 0) {
      return false;
    }
    return cursorId == null || item.recordId().compareTo(cursorId) < 0;
  }
}
