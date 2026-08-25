package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.OperationalEventEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.OperationalEventJpaRepository;
import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.data.domain.PageRequest;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaOperationalEventStoreAdapter implements OperationalEventStorePort {

  private static final TypeReference<Map<String, String>> METADATA_TYPE = new TypeReference<>() {};

  private final OperationalEventJpaRepository repository;
  private final ObjectMapper objectMapper;

  public JpaOperationalEventStoreAdapter(
      OperationalEventJpaRepository repository, ObjectMapper objectMapper) {
    this.repository = repository;
    this.objectMapper = objectMapper;
  }

  @Override
  @Transactional
  public void append(OperationalEvent event) {
    repository.save(toEntity(event));
  }

  @Override
  public List<OperationalEvent> findByExecutionId(String executionId) {
    return repository.findByExecutionIdOrderByOccurredAtAscEventIdAsc(executionId).stream()
        .map(this::toModel)
        .toList();
  }

  @Override
  public List<OperationalEvent> findByExecutionId(
      String executionId, Instant from, Instant to) {
    if (from == null || to == null) {
      return OperationalEventStorePort.super.findByExecutionId(executionId, from, to);
    }
    return repository
        .findByExecutionIdAndOccurredAtBetweenOrderByOccurredAtAscEventIdAsc(
            executionId, from, to)
        .stream()
        .map(this::toModel)
        .toList();
  }

  @Override
  public List<OperationalEvent> findOccurredBetween(
      Instant fromInclusive, Instant toInclusive, int maxResults) {
    if (maxResults <= 0) {
      return List.of();
    }
    return repository
        .findByOccurredAtBetweenOrderByOccurredAtAscEventIdAsc(
            fromInclusive, toInclusive, PageRequest.of(0, maxResults))
        .stream()
        .map(this::toModel)
        .toList();
  }

  private OperationalEventEntity toEntity(OperationalEvent event) {
    OperationalEventEntity entity = new OperationalEventEntity();
    entity.setEventId(event.eventId());
    entity.setSchemaVersion(event.schemaVersion());
    entity.setEventType(event.eventType());
    entity.setCategory(event.category());
    entity.setOccurredAt(event.occurredAt());
    entity.setExecutionId(event.executionId());
    entity.setInteractionId(event.interactionId());
    entity.setCorrelationId(event.correlationId());
    entity.setSource(event.source());
    entity.setOutcome(event.outcome());
    entity.setDurationMs(event.durationMs());
    try {
      entity.setMetadataJson(objectMapper.writeValueAsString(event.metadata()));
    } catch (Exception failure) {
      throw new IllegalStateException("Could not serialize operational event metadata", failure);
    }
    return entity;
  }

  private OperationalEvent toModel(OperationalEventEntity entity) {
    try {
      return new OperationalEvent(
          entity.getEventId(),
          entity.getSchemaVersion(),
          entity.getEventType(),
          entity.getCategory(),
          entity.getOccurredAt(),
          entity.getExecutionId(),
          entity.getInteractionId(),
          entity.getCorrelationId(),
          entity.getSource(),
          entity.getOutcome(),
          entity.getDurationMs(),
          objectMapper.readValue(entity.getMetadataJson(), METADATA_TYPE));
    } catch (Exception failure) {
      throw new IllegalStateException("Could not deserialize operational event metadata", failure);
    }
  }
}
