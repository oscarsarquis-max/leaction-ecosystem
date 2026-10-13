package br.com.banco.spider.operational.monitor;

import java.time.Instant;

public final class MonitorProjectionMerge {

  private MonitorProjectionMerge() {}

  public static MonitorProjectionRecord apply(MonitorProjectionRecord current, MonitorProjectionRecord incoming) {
    if (current == null) {
      return incoming;
    }
    if (incoming == null) {
      return current;
    }
    String technical = incoming.technicalState();
    if (MonitorProjectionStates.regressesTechnical(current.technicalState(), technical)) {
      technical = current.technicalState();
    }
    String financial = incoming.financialState();
    if (MonitorProjectionStates.regressesFinancial(current.financialState(), financial)) {
      financial = current.financialState();
    }
    Instant lastSynced = later(current.lastSyncedAt(), incoming.lastSyncedAt());
    return incoming.toBuilder()
        .createdAt(current.createdAt() == null ? incoming.createdAt() : current.createdAt())
        .retentionUntil(current.retentionUntil() == null ? incoming.retentionUntil() : current.retentionUntil())
        .technicalState(technical)
        .financialState(financial)
        .commercialState(firstNonBlank(incoming.commercialState(), current.commercialState()))
        .creditState(firstNonBlank(incoming.creditState(), current.creditState()))
        .relatedSyncId(firstNonBlank(incoming.relatedSyncId(), current.relatedSyncId()))
        .relatedPaymentId(firstNonBlank(incoming.relatedPaymentId(), current.relatedPaymentId()))
        .relatedInteractionId(firstNonBlank(incoming.relatedInteractionId(), current.relatedInteractionId()))
        .syncRunId(firstNonBlank(incoming.syncRunId(), current.syncRunId()))
        .pagesConsulted(max(current.pagesConsulted(), incoming.pagesConsulted()))
        .foundCount(sum(current.foundCount(), incoming.foundCount(), incoming.kind()))
        .newCount(sum(current.newCount(), incoming.newCount(), incoming.kind()))
        .updatedCount(sum(current.updatedCount(), incoming.updatedCount(), incoming.kind()))
        .ignoredCount(sum(current.ignoredCount(), incoming.ignoredCount(), incoming.kind()))
        .failedCount(sum(current.failedCount(), incoming.failedCount(), incoming.kind()))
        .lastSyncedAt(lastSynced)
        .executionId(current.executionId())
        .projectionVersion(current.projectionVersion() + 1)
        .build();
  }

  private static Instant later(Instant left, Instant right) {
    if (left == null) {
      return right;
    }
    if (right == null) {
      return left;
    }
    return right.isAfter(left) ? right : left;
  }

  private static String firstNonBlank(String preferred, String fallback) {
    return preferred == null || preferred.isBlank() ? fallback : preferred;
  }

  private static Integer max(Integer left, Integer right) {
    if (left == null) {
      return right;
    }
    if (right == null) {
      return left;
    }
    return Math.max(left, right);
  }

  private static Integer sum(Integer current, Integer incoming, String kind) {
    if (!MonitorProjectionRecord.KIND_SYNC.equals(kind)) {
      return incoming == null ? current : incoming;
    }
    if (current == null) {
      return incoming;
    }
    if (incoming == null) {
      return current;
    }
    return incoming >= current ? incoming : current;
  }
}
