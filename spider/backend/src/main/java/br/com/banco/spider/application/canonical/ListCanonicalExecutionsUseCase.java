package br.com.banco.spider.application.canonical;

import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.infrastructure.persistence.BlockingPersistenceSupport;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class ListCanonicalExecutionsUseCase {

  private static final int DEFAULT_LIMIT = 20;

  private final ExecutionControlStorePort controlStore;
  private final BlockingPersistenceSupport blocking;

  public ListCanonicalExecutionsUseCase(
      ExecutionControlStorePort controlStore, BlockingPersistenceSupport blocking) {
    this.controlStore = controlStore;
    this.blocking = blocking;
  }

  public Mono<List<Map<String, Object>>> listOwned(String principalRef, int limit) {
    Objects.requireNonNull(principalRef, "principalRef");
    int bounded = Math.min(Math.max(limit, 1), 50);
    return blocking.defer(
        () ->
            controlStore.listRecent(bounded * 4, null, null).stream()
                .filter(r -> principalRef.equals(r.ownerPrincipalRef()))
                .limit(bounded)
                .map(this::summary)
                .toList());
  }

  private Map<String, Object> summary(ExecutionControlRecord record) {
    Map<String, Object> row = new LinkedHashMap<>();
    row.put("executionId", record.executionId());
    row.put("state", record.state() == null ? null : record.state().name());
    row.put("technicalStatus", record.technicalStatus() == null ? null : record.technicalStatus().name());
    row.put("routeCode", record.routeCode());
    row.put("startedAt", record.startedAt() == null ? null : record.startedAt().toString());
    row.put("completedAt", record.completedAt() == null ? null : record.completedAt().toString());
    row.put("durationMs", durationMs(record));
    return row;
  }

  private static Long durationMs(ExecutionControlRecord record) {
    if (record.startedAt() == null) {
      return null;
    }
    var end = record.completedAt() != null ? record.completedAt() : record.lastUpdatedAt();
    if (end == null) {
      return null;
    }
    return Duration.between(record.startedAt(), end).toMillis();
  }
}
