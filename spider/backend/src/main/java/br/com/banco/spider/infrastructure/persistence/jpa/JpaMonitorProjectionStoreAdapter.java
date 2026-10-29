package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.MonitorProjectionEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.MonitorProjectionJpaRepository;
import br.com.banco.spider.operational.monitor.MonitorProjectionPort;
import br.com.banco.spider.operational.monitor.MonitorProjectionRecord;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.monitor.persistence.adapter", havingValue = "hibernate")
public class JpaMonitorProjectionStoreAdapter implements MonitorProjectionPort {

  private final MonitorProjectionJpaRepository repository;

  public JpaMonitorProjectionStoreAdapter(MonitorProjectionJpaRepository repository) {
    this.repository = repository;
  }

  @Override
  @Transactional
  public void upsert(MonitorProjectionRecord record) {
    if (record == null || record.recordId() == null || record.recordId().isBlank()) {
      return;
    }
    MonitorProjectionRecord merged =
        br.com.banco.spider.operational.monitor.MonitorProjectionMerge.apply(
            findById(record.recordId()).orElse(null), record);
    repository.save(toEntity(merged));
  }

  @Override
  public Optional<MonitorProjectionRecord> findById(String recordId) {
    if (recordId == null || recordId.isBlank()) {
      return Optional.empty();
    }
    return repository.findById(recordId).map(this::toModel);
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
    String like =
        query == null || query.isBlank() ? null : "%" + query.trim().toLowerCase(Locale.ROOT) + "%";
    Instant clock = now == null ? Instant.now() : now;
    return repository
        .search(
            clock,
            blankToNull(kind),
            blankToNull(origin),
            like,
            cursorUpdatedAt,
            cursorId,
            PageRequest.of(0, Math.max(1, limit)))
        .stream()
        .map(this::toModel)
        .toList();
  }

  @Override
  @Transactional
  public int purgeExpired(Instant now) {
    Instant clock = now == null ? Instant.now() : now;
    return repository.purgeExpired(clock);
  }

  @Override
  public boolean isDurable() {
    return true;
  }

  private static MonitorProjectionEntity toEntity(MonitorProjectionRecord record) {
    MonitorProjectionEntity entity = new MonitorProjectionEntity();
    entity.setRecordId(record.recordId());
    entity.setKind(record.kind());
    entity.setSatelliteId(record.satelliteId());
    entity.setSatelliteRole(record.satelliteRole());
    entity.setOrigin(record.origin());
    entity.setMessageId(record.messageId());
    entity.setCorrelationId(record.correlationId());
    entity.setExecutionId(record.executionId());
    entity.setExternalRef(record.externalRef());
    entity.setCapability(record.capability());
    entity.setContractVersion(record.contractVersion());
    entity.setCompanyId(record.companyId());
    entity.setEnvironment(record.environment());
    entity.setTechnicalState(record.technicalState());
    entity.setCommercialState(record.commercialState());
    entity.setFinancialState(record.financialState());
    entity.setCreditState(record.creditState());
    entity.setCurrentComponent(record.currentComponent());
    entity.setObjective(record.objective());
    entity.setCreatedAt(record.createdAt());
    entity.setUpdatedAt(record.updatedAt());
    entity.setLastSyncedAt(record.lastSyncedAt());
    entity.setDiscoveryOrigin(record.discoveryOrigin());
    entity.setEventKey(record.eventKey());
    entity.setProjectionVersion(record.projectionVersion());
    entity.setRetentionUntil(record.retentionUntil());
    entity.setSyncRunId(record.syncRunId());
    entity.setRelatedSyncId(record.relatedSyncId());
    entity.setRelatedPaymentId(record.relatedPaymentId());
    entity.setRelatedInteractionId(record.relatedInteractionId());
    entity.setPagesConsulted(record.pagesConsulted());
    entity.setFoundCount(record.foundCount());
    entity.setNewCount(record.newCount());
    entity.setUpdatedCount(record.updatedCount());
    entity.setIgnoredCount(record.ignoredCount());
    entity.setFailedCount(record.failedCount());
    return entity;
  }

  private MonitorProjectionRecord toModel(MonitorProjectionEntity entity) {
    return MonitorProjectionRecord.builder()
        .recordId(entity.getRecordId())
        .kind(entity.getKind())
        .satelliteId(entity.getSatelliteId())
        .satelliteRole(entity.getSatelliteRole())
        .origin(entity.getOrigin())
        .messageId(entity.getMessageId())
        .correlationId(entity.getCorrelationId())
        .executionId(entity.getExecutionId())
        .externalRef(entity.getExternalRef())
        .capability(entity.getCapability())
        .contractVersion(entity.getContractVersion())
        .companyId(entity.getCompanyId())
        .environment(entity.getEnvironment())
        .technicalState(entity.getTechnicalState())
        .commercialState(entity.getCommercialState())
        .financialState(entity.getFinancialState())
        .creditState(entity.getCreditState())
        .currentComponent(entity.getCurrentComponent())
        .objective(entity.getObjective())
        .createdAt(entity.getCreatedAt())
        .updatedAt(entity.getUpdatedAt())
        .lastSyncedAt(entity.getLastSyncedAt())
        .discoveryOrigin(entity.getDiscoveryOrigin())
        .eventKey(entity.getEventKey())
        .projectionVersion(entity.getProjectionVersion())
        .retentionUntil(entity.getRetentionUntil())
        .syncRunId(entity.getSyncRunId())
        .relatedSyncId(entity.getRelatedSyncId())
        .relatedPaymentId(entity.getRelatedPaymentId())
        .relatedInteractionId(entity.getRelatedInteractionId())
        .pagesConsulted(entity.getPagesConsulted())
        .foundCount(entity.getFoundCount())
        .newCount(entity.getNewCount())
        .updatedCount(entity.getUpdatedCount())
        .ignoredCount(entity.getIgnoredCount())
        .failedCount(entity.getFailedCount())
        .build();
  }

  private static String blankToNull(String value) {
    return value == null || value.isBlank() ? null : value;
  }
}
