package br.com.segsense.infrastructure.link;

import br.com.segsense.application.link.PublishedContextLinkRepository;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.link.ContextLinkEvent;
import br.com.segsense.domain.link.ContextLinkEventType;
import br.com.segsense.domain.link.ContextLinkStatus;
import br.com.segsense.domain.link.PublishedContextLink;
import br.com.segsense.domain.link.PublisherContextBinding;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.stereotype.Repository;

@Repository
public class JpaPublishedContextLinkRepository implements PublishedContextLinkRepository {

  private final PublishedContextLinkSpringRepository links;
  private final PublishedContextLinkBindingSpringRepository bindings;
  private final PublishedContextLinkEventSpringRepository events;

  public JpaPublishedContextLinkRepository(
      PublishedContextLinkSpringRepository links,
      PublishedContextLinkBindingSpringRepository bindings,
      PublishedContextLinkEventSpringRepository events) {
    this.links = links;
    this.bindings = bindings;
    this.events = events;
  }

  @Override
  public PublishedContextLink saveNew(PublishedContextLink link, ContextLinkEvent issued) {
    PublishedContextLinkJpaEntity entity = new PublishedContextLinkJpaEntity();
    copyMutable(entity, link);
    entity.setIssuedAt(link.issuedAt());
    entity.setIssuedBy(link.issuedBy());
    entity.setIssuedCorrelationId(link.issuedCorrelationId());
    try {
      links.saveAndFlush(entity);
      for (PublisherContextBinding binding : link.bindings()) {
        bindings.save(toBindingEntity(link.id(), link.opportunityRevisionId(), binding));
      }
      events.save(toEventEntity(issued));
      links.flush();
      bindings.flush();
      events.flush();
      return loadRequired(link.id());
    } catch (DataIntegrityViolationException ex) {
      throw duplicateOrRethrow(ex);
    }
  }

  @Override
  public PublishedContextLink saveRevocation(PublishedContextLink link, ContextLinkEvent revoked) {
    PublishedContextLinkJpaEntity entity =
        links.findById(link.id()).orElseThrow(br.com.segsense.domain.catalog.ResourceNotFoundException::new);
    entity.setStatus(link.status().name());
    entity.setRevokedAt(link.revokedAt());
    entity.setRevokedBy(link.revokedBy());
    entity.setRevocationReason(link.revocationReason());
    entity.setRevokedCorrelationId(link.revokedCorrelationId());
    try {
      links.saveAndFlush(entity);
      events.saveAndFlush(toEventEntity(revoked));
      return loadRequired(link.id());
    } catch (ObjectOptimisticLockingFailureException ex) {
      throw ex;
    } catch (DataIntegrityViolationException ex) {
      throw duplicateOrRethrow(ex);
    }
  }

  @Override
  public Optional<PublishedContextLink> findByScope(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId, UUID linkId) {
    return links
        .findByIdAndPublisherIdAndChannelIdAndEnvironmentIdAndOpportunityId(
            linkId, publisherId, channelId, environmentId, opportunityId)
        .map(this::toDomain);
  }

  @Override
  public Optional<PublishedContextLink> findByTokenDigest(byte[] digest) {
    return links.findByTokenDigest(digest).map(this::toDomain);
  }

  @Override
  public List<PublishedContextLink> listAfter(
      UUID opportunityId, InstantCursor cursor, boolean hasCursor, int limit) {
    Instant issuedAt = hasCursor ? cursor.occurredAt() : Instant.EPOCH;
    UUID id = hasCursor ? cursor.id() : new UUID(0L, 0L);
    return links
        .listAfter(opportunityId, hasCursor, issuedAt, id, PageRequest.of(0, limit))
        .stream()
        .map(this::toDomain)
        .toList();
  }

  @Override
  public List<ContextLinkEvent> listEventsAfter(
      UUID linkId, InstantCursor cursor, boolean hasCursor, int limit) {
    Instant occurredAt = hasCursor ? cursor.occurredAt() : Instant.EPOCH;
    UUID id = hasCursor ? cursor.id() : new UUID(0L, 0L);
    List<ContextLinkEvent> result = new ArrayList<>();
    for (PublishedContextLinkEventJpaEntity entity :
        events.listAfter(linkId, hasCursor, occurredAt, id, PageRequest.of(0, limit))) {
      result.add(toEvent(entity));
    }
    return result;
  }

  private PublishedContextLink loadRequired(UUID id) {
    return toDomain(links.findById(id).orElseThrow(br.com.segsense.domain.catalog.ResourceNotFoundException::new));
  }

  private PublishedContextLink toDomain(PublishedContextLinkJpaEntity entity) {
    List<PublisherContextBinding> bound = new ArrayList<>();
    for (PublishedContextLinkBindingJpaEntity binding :
        bindings.findByLinkIdOrderByFieldKeyAsc(entity.getId())) {
      bound.add(
          PublisherContextBinding.restore(
              binding.getId(),
              binding.getFieldKey(),
              ContextFieldType.valueOf(binding.getFieldType()),
              ContextFieldSource.valueOf(binding.getFieldSource()),
              binding.getTextValue(),
              binding.getNumberValue(),
              binding.getBooleanValue(),
              binding.getDateValue()));
    }
    return PublishedContextLink.restore(
        entity.getId(),
        entity.getPublisherId(),
        entity.getChannelId(),
        entity.getEnvironmentId(),
        entity.getOpportunityId(),
        entity.getRevisionNumber(),
        entity.getOpportunityRevisionId(),
        entity.getPlacementKey(),
        entity.getLabel(),
        entity.getTokenDigest(),
        entity.getTokenHint(),
        ContextLinkStatus.valueOf(entity.getStatus()),
        entity.getIssuedAt(),
        entity.getIssuedBy(),
        entity.getExpiresAt(),
        entity.getRevokedAt(),
        entity.getRevokedBy(),
        entity.getRevocationReason(),
        entity.getVersion() == null ? 0L : entity.getVersion(),
        entity.getIssuedCorrelationId(),
        entity.getRevokedCorrelationId(),
        bound);
  }

  private static void copyMutable(PublishedContextLinkJpaEntity entity, PublishedContextLink link) {
    entity.setId(link.id());
    entity.setPublisherId(link.publisherId());
    entity.setChannelId(link.channelId());
    entity.setEnvironmentId(link.environmentId());
    entity.setOpportunityId(link.opportunityId());
    entity.setRevisionNumber(link.revisionNumber());
    entity.setOpportunityRevisionId(link.opportunityRevisionId());
    entity.setPlacementKey(link.placementKey());
    entity.setLabel(link.label());
    entity.setTokenDigest(link.tokenDigest());
    entity.setTokenHint(link.tokenHint());
    entity.setStatus(link.status().name());
    entity.setExpiresAt(link.expiresAt());
    entity.setRevokedAt(link.revokedAt());
    entity.setRevokedBy(link.revokedBy());
    entity.setRevocationReason(link.revocationReason());
    entity.setRevokedCorrelationId(link.revokedCorrelationId());
  }

  private static PublishedContextLinkBindingJpaEntity toBindingEntity(
      UUID linkId, UUID opportunityRevisionId, PublisherContextBinding binding) {
    PublishedContextLinkBindingJpaEntity entity = new PublishedContextLinkBindingJpaEntity();
    entity.setId(binding.id());
    entity.setLinkId(linkId);
    entity.setOpportunityRevisionId(opportunityRevisionId);
    entity.setFieldKey(binding.fieldKey());
    entity.setFieldType(binding.fieldType().name());
    entity.setFieldSource(binding.fieldSource().name());
    entity.setTextValue(binding.textValue());
    entity.setNumberValue(binding.numberValue());
    entity.setBooleanValue(binding.booleanValue());
    entity.setDateValue(binding.dateValue());
    return entity;
  }

  private static PublishedContextLinkEventJpaEntity toEventEntity(ContextLinkEvent event) {
    PublishedContextLinkEventJpaEntity entity = new PublishedContextLinkEventJpaEntity();
    entity.setId(event.id());
    entity.setLinkId(event.linkId());
    entity.setEventType(event.eventType().name());
    entity.setOccurredAt(event.occurredAt());
    entity.setActorSubject(event.actorSubject());
    entity.setCorrelationId(event.correlationId());
    return entity;
  }

  private static ContextLinkEvent toEvent(PublishedContextLinkEventJpaEntity entity) {
    return new ContextLinkEvent(
        entity.getId(),
        entity.getLinkId(),
        ContextLinkEventType.valueOf(entity.getEventType()),
        entity.getOccurredAt(),
        entity.getActorSubject(),
        entity.getCorrelationId());
  }

  private static RuntimeException duplicateOrRethrow(DataIntegrityViolationException ex) {
    String detail = String.valueOf(ex.getMostSpecificCause().getMessage());
    if (detail.contains("published_context_link_placement_unique")) {
      return new DuplicateResourceKeyException(
          "LINK_PLACEMENT_CONFLICT",
          "Já existe um link com esta chave de posicionamento nesta revisão.");
    }
    return ex;
  }
}
