package br.com.banco.spider.operational.monitor;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface MonitorProjectionPort {

  void upsert(MonitorProjectionRecord record);

  Optional<MonitorProjectionRecord> findById(String recordId);

  List<MonitorProjectionRecord> search(
      String query, String origin, String kind, Instant now, int limit, Instant cursorUpdatedAt, String cursorId);

  int purgeExpired(Instant now);

  default boolean isDurable() {
    return false;
  }
}
