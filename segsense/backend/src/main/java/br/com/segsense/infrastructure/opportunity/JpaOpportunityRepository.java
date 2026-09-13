package br.com.segsense.infrastructure.opportunity;

import br.com.segsense.application.catalog.CatalogCursor;
import br.com.segsense.application.opportunity.OpportunityRepository;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.opportunity.ContextFieldDefinition;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.ContextMode;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.DecisionOutcome;
import br.com.segsense.domain.opportunity.FieldClassification;
import br.com.segsense.domain.opportunity.GovernanceEffect;
import br.com.segsense.domain.opportunity.LifecycleEvent;
import br.com.segsense.domain.opportunity.LifecycleEventType;
import br.com.segsense.domain.opportunity.OpportunityContent;
import br.com.segsense.domain.opportunity.OpportunityDecision;
import br.com.segsense.domain.opportunity.OpportunityRevision;
import br.com.segsense.domain.opportunity.OpportunityStatus;
import br.com.segsense.domain.opportunity.OpportunitySubmission;
import br.com.segsense.domain.opportunity.SubmissionAlreadyOpenException;
import br.com.segsense.domain.opportunity.SubmissionStatus;
import jakarta.persistence.EntityManager;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;

@Repository
public class JpaOpportunityRepository implements OpportunityRepository {

  private final OpportunitySpringRepository opportunities;
  private final OpportunityRevisionSpringRepository revisions;
  private final OpportunityRevisionFieldSpringRepository fields;
  private final OpportunitySubmissionSpringRepository submissions;
  private final OpportunityDecisionSpringRepository decisions;
  private final LifecycleEventSpringRepository events;
  private final EntityManager entityManager;

  public JpaOpportunityRepository(
      OpportunitySpringRepository opportunities,
      OpportunityRevisionSpringRepository revisions,
      OpportunityRevisionFieldSpringRepository fields,
      OpportunitySubmissionSpringRepository submissions,
      OpportunityDecisionSpringRepository decisions,
      LifecycleEventSpringRepository events,
      EntityManager entityManager) {
    this.opportunities = opportunities;
    this.revisions = revisions;
    this.fields = fields;
    this.submissions = submissions;
    this.decisions = decisions;
    this.events = events;
    this.entityManager = entityManager;
  }

  @Override
  public ContextualOpportunity saveNew(ContextualOpportunity opportunity) {
    OpportunityJpaEntity entity = new OpportunityJpaEntity();
    copyIdentity(entity, opportunity);
    entity.setCreatedAt(opportunity.createdAt());
    entity.setCreatedBy(opportunity.createdBy());
    try {
      opportunities.saveAndFlush(entity);
      insertRevision(opportunity.id(), opportunity.current());
      return loadRequired(
          opportunity.publisherId(),
          opportunity.channelId(),
          opportunity.environmentId(),
          opportunity.id());
    } catch (DataIntegrityViolationException ex) {
      throw duplicateOrRethrow(ex);
    }
  }

  @Override
  public ContextualOpportunity saveNewRevision(ContextualOpportunity opportunity) {
    OpportunityJpaEntity entity =
        opportunities.findById(opportunity.id()).orElseThrow(IllegalStateException::new);
    entity.setCurrentRevision(opportunity.currentRevision());
    entity.setUpdatedAt(opportunity.updatedAt());
    entity.setUpdatedBy(opportunity.updatedBy());
    try {
      opportunities.saveAndFlush(entity);
      insertRevision(opportunity.id(), opportunity.current());
      return loadRequired(
          opportunity.publisherId(),
          opportunity.channelId(),
          opportunity.environmentId(),
          opportunity.id());
    } catch (DataIntegrityViolationException ex) {
      throw duplicateOrRethrow(ex);
    }
  }

  @Override
  public Optional<ContextualOpportunity> findByScope(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId) {
    return opportunities
        .findByIdAndPublisherIdAndChannelIdAndEnvironmentId(
            opportunityId, publisherId, channelId, environmentId)
        .map(this::toDomain);
  }

  @Override
  public boolean existsByEnvironmentIdAndKey(UUID environmentId, ResourceKey key) {
    return opportunities.existsByEnvironmentIdAndKey(environmentId, key.value());
  }

  @Override
  public List<ContextualOpportunity> listAfter(
      UUID publisherId, UUID channelId, UUID environmentId, CatalogCursor after, int limit) {
    boolean hasCursor = after != null;
    Instant createdAt = hasCursor ? after.createdAt() : Instant.EPOCH;
    UUID id = hasCursor ? after.id() : new UUID(0, 0);
    return opportunities
        .listAfter(
            publisherId,
            channelId,
            environmentId,
            hasCursor,
            createdAt,
            id,
            PageRequest.of(0, limit))
        .stream()
        .map(this::toDomain)
        .toList();
  }

  @Override
  public List<OpportunityRevision> listRevisionsAfter(
      UUID opportunityId, Integer afterRevisionNumber, int limit) {
    boolean hasCursor = afterRevisionNumber != null;
    int after = hasCursor ? afterRevisionNumber : 0;
    return revisions
        .listAfter(opportunityId, hasCursor, after, PageRequest.of(0, limit))
        .stream()
        .map(this::toRevision)
        .toList();
  }

  @Override
  public Optional<OpportunityRevision> findRevision(UUID opportunityId, int revisionNumber) {
    return revisions
        .findByOpportunityIdAndRevisionNumber(opportunityId, revisionNumber)
        .map(this::toRevision);
  }

  @Override
  public ContextualOpportunity saveGovernance(
      ContextualOpportunity opportunity, GovernanceEffect effect) {
    OpportunityJpaEntity entity =
        opportunities.findById(opportunity.id()).orElseThrow(IllegalStateException::new);
    try {
      OpportunitySubmission submission = effect.submission();
      if (submission != null && submissions.findById(submission.id()).isEmpty()) {
        persistSubmission(submission);
        submissions.flush();
      }
      copyIdentity(entity, opportunity);
      opportunities.saveAndFlush(entity);
      if (effect.decision() != null) {
        persistDecision(effect.decision());
        decisions.flush();
      }
      persistEvent(effect.event());
      events.flush();
      return loadRequired(
          opportunity.publisherId(),
          opportunity.channelId(),
          opportunity.environmentId(),
          opportunity.id());
    } catch (DataIntegrityViolationException ex) {
      throw duplicateOrRethrow(ex);
    }
  }

  @Override
  public Optional<OpportunitySubmission> findOpenSubmission(UUID opportunityId) {
    return opportunities
        .findById(opportunityId)
        .filter(entity -> entity.getOpenSubmissionId() != null)
        .flatMap(entity -> submissions.findById(entity.getOpenSubmissionId()))
        .filter(submission -> submission.getOpportunityId().equals(opportunityId))
        .filter(submission -> decisions.findBySubmissionId(submission.getId()).isEmpty())
        .map(this::toSubmission);
  }

  @Override
  public Optional<OpportunityDecision> findLatestDecision(UUID opportunityId) {
    return decisions
        .findFirstByOpportunityIdOrderByDecidedAtDesc(opportunityId)
        .map(this::toDecision);
  }

  @Override
  public List<LifecycleEvent> listEventsAfter(
      UUID opportunityId, Instant occurredAt, UUID afterId, boolean hasCursor, int limit) {
    Instant cursorTime = hasCursor ? occurredAt : Instant.EPOCH;
    UUID cursorId = hasCursor ? afterId : new UUID(0, 0);
    return events
        .listAfter(opportunityId, hasCursor, cursorTime, cursorId, PageRequest.of(0, limit))
        .stream()
        .map(this::toEvent)
        .toList();
  }

  private ContextualOpportunity loadRequired(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId) {
    return findByScope(publisherId, channelId, environmentId, opportunityId)
        .orElseThrow(IllegalStateException::new);
  }

  private static void copyIdentity(OpportunityJpaEntity entity, ContextualOpportunity opportunity) {
    entity.setId(opportunity.id());
    entity.setPublisherId(opportunity.publisherId());
    entity.setChannelId(opportunity.channelId());
    entity.setEnvironmentId(opportunity.environmentId());
    entity.setKey(opportunity.key().value());
    entity.setStatus(opportunity.status().name());
    entity.setCurrentRevision(opportunity.currentRevision());
    entity.setUpdatedAt(opportunity.updatedAt());
    entity.setUpdatedBy(opportunity.updatedBy());
    entity.setSubmittedRevision(opportunity.submittedRevision());
    entity.setApprovedRevision(opportunity.approvedRevision());
    entity.setOpenSubmissionId(opportunity.openSubmissionId());
    entity.setSubmittedBy(opportunity.submittedBy());
    entity.setApprovedBy(opportunity.approvedBy());
  }

  private void persistSubmission(OpportunitySubmission submission) {
    OpportunitySubmissionJpaEntity entity = new OpportunitySubmissionJpaEntity();
    entity.setId(submission.id());
    entity.setOpportunityId(submission.opportunityId());
    entity.setRevisionNumber(submission.revisionNumber());
    entity.setSubmittedAt(submission.submittedAt());
    entity.setSubmittedBy(submission.submittedBy());
    entity.setCorrelationId(submission.correlationId());
    entity.setStatus(submission.status().name());
    entityManager.persist(entity);
  }

  private void persistDecision(OpportunityDecision decision) {
    OpportunityDecisionJpaEntity entity = new OpportunityDecisionJpaEntity();
    entity.setId(decision.id());
    entity.setSubmissionId(decision.submissionId());
    entity.setOpportunityId(decision.opportunityId());
    entity.setRevisionNumber(decision.revisionNumber());
    entity.setOutcome(decision.outcome().name());
    entity.setDecidedAt(decision.decidedAt());
    entity.setDecidedBy(decision.decidedBy());
    entity.setJustification(decision.justification());
    entity.setCorrelationId(decision.correlationId());
    entityManager.persist(entity);
  }

  private void persistEvent(LifecycleEvent event) {
    LifecycleEventJpaEntity entity = new LifecycleEventJpaEntity();
    entity.setId(event.id());
    entity.setOpportunityId(event.opportunityId());
    entity.setRevisionNumber(event.revisionNumber());
    entity.setEventType(event.type().name());
    entity.setPreviousStatus(event.previousStatus().name());
    entity.setNewStatus(event.newStatus().name());
    entity.setActorSubjectId(event.actorSubjectId());
    entity.setOccurredAt(event.occurredAt());
    entity.setJustification(event.justification());
    entity.setCorrelationId(event.correlationId());
    entityManager.persist(entity);
  }

  private void insertRevision(UUID opportunityId, OpportunityRevision revision) {
    OpportunityRevisionJpaEntity entity = new OpportunityRevisionJpaEntity();
    OpportunityContent content = revision.content();
    entity.setId(revision.id());
    entity.setOpportunityId(opportunityId);
    entity.setRevisionNumber(revision.revisionNumber());
    entity.setTitle(content.title());
    entity.setContextMode(content.contextMode().name());
    entity.setContextSummaryTemplate(content.contextSummaryTemplate());
    entity.setObjectiveTemplate(content.objectiveTemplate());
    entity.setCallToActionLabel(content.callToActionLabel());
    entity.setValidFrom(content.validFrom());
    entity.setValidUntil(content.validUntil());
    entity.setCreatedAt(revision.createdAt());
    entity.setCreatedBy(revision.createdBy());
    revisions.saveAndFlush(entity);
    List<OpportunityRevisionFieldJpaEntity> fieldEntities = new ArrayList<>();
    for (ContextFieldDefinition field : content.contextFields()) {
      OpportunityRevisionFieldJpaEntity fieldEntity = new OpportunityRevisionFieldJpaEntity();
      fieldEntity.setId(UUID.randomUUID());
      fieldEntity.setOpportunityRevisionId(revision.id());
      fieldEntity.setFieldKey(field.key());
      fieldEntity.setLabel(field.label());
      fieldEntity.setType(field.type().name());
      fieldEntity.setRequired(field.required());
      fieldEntity.setSource(field.source().name());
      fieldEntity.setClassification(field.classification().name());
      fieldEntity.setPosition(field.position());
      if (field.type() == ContextFieldType.ENUM) {
        fieldEntity.setAllowedValues(field.allowedValues().toArray(String[]::new));
      } else {
        fieldEntity.setAllowedValues(null);
      }
      fieldEntities.add(fieldEntity);
    }
    if (!fieldEntities.isEmpty()) {
      fields.saveAll(fieldEntities);
      fields.flush();
    }
  }

  private ContextualOpportunity toDomain(OpportunityJpaEntity entity) {
    OpportunityRevision current =
        revisions
            .findByOpportunityIdAndRevisionNumber(entity.getId(), entity.getCurrentRevision())
            .map(this::toRevision)
            .orElseThrow(IllegalStateException::new);
    return ContextualOpportunity.restore(
        entity.getId(),
        entity.getPublisherId(),
        entity.getChannelId(),
        entity.getEnvironmentId(),
        ResourceKey.restored(entity.getKey()),
        OpportunityStatus.valueOf(entity.getStatus()),
        entity.getCurrentRevision(),
        entity.getVersion() == null ? 0L : entity.getVersion(),
        entity.getCreatedAt(),
        entity.getUpdatedAt(),
        entity.getCreatedBy(),
        entity.getUpdatedBy(),
        current,
        entity.getSubmittedRevision(),
        entity.getApprovedRevision(),
        entity.getOpenSubmissionId(),
        entity.getSubmittedBy(),
        entity.getApprovedBy());
  }

  private OpportunitySubmission toSubmission(OpportunitySubmissionJpaEntity entity) {
    return new OpportunitySubmission(
        entity.getId(),
        entity.getOpportunityId(),
        entity.getRevisionNumber(),
        entity.getSubmittedAt(),
        entity.getSubmittedBy(),
        entity.getCorrelationId(),
        SubmissionStatus.valueOf(entity.getStatus()));
  }

  private OpportunityDecision toDecision(OpportunityDecisionJpaEntity entity) {
    return new OpportunityDecision(
        entity.getId(),
        entity.getSubmissionId(),
        entity.getOpportunityId(),
        entity.getRevisionNumber(),
        DecisionOutcome.valueOf(entity.getOutcome()),
        entity.getDecidedAt(),
        entity.getDecidedBy(),
        entity.getJustification(),
        entity.getCorrelationId());
  }

  private LifecycleEvent toEvent(LifecycleEventJpaEntity entity) {
    return new LifecycleEvent(
        entity.getId(),
        entity.getOpportunityId(),
        entity.getRevisionNumber(),
        LifecycleEventType.valueOf(entity.getEventType()),
        OpportunityStatus.valueOf(entity.getPreviousStatus()),
        OpportunityStatus.valueOf(entity.getNewStatus()),
        entity.getActorSubjectId(),
        entity.getOccurredAt(),
        entity.getJustification(),
        entity.getCorrelationId());
  }

  private OpportunityRevision toRevision(OpportunityRevisionJpaEntity entity) {
    List<ContextFieldDefinition> definitions = new ArrayList<>();
    for (OpportunityRevisionFieldJpaEntity field :
        fields.findByOpportunityRevisionIdOrderByPositionAsc(entity.getId())) {
      List<String> allowed =
          field.getAllowedValues() == null ? List.of() : List.of(field.getAllowedValues());
      definitions.add(
          ContextFieldDefinition.parse(
              field.getFieldKey(),
              field.getLabel(),
              ContextFieldType.valueOf(field.getType()),
              field.isRequired(),
              ContextFieldSource.valueOf(field.getSource()),
              FieldClassification.valueOf(field.getClassification()),
              allowed.isEmpty() ? null : allowed,
              field.getPosition()));
    }
    OpportunityContent content =
        OpportunityContent.parse(
            entity.getTitle(),
            ContextMode.valueOf(entity.getContextMode()),
            entity.getContextSummaryTemplate(),
            entity.getObjectiveTemplate(),
            entity.getCallToActionLabel(),
            entity.getValidFrom(),
            entity.getValidUntil(),
            definitions);
    return new OpportunityRevision(
        entity.getId(),
        entity.getRevisionNumber(),
        content,
        entity.getCreatedAt(),
        entity.getCreatedBy());
  }

  private static RuntimeException duplicateOrRethrow(DataIntegrityViolationException ex) {
    String detail = String.valueOf(ex.getMostSpecificCause().getMessage());
    if (detail.contains("opportunity_key_unique")) {
      return new DuplicateResourceKeyException(
          "OPPORTUNITY_KEY_CONFLICT", "Já existe uma oportunidade com esta chave neste ambiente.");
    }
    if (detail.contains("opportunity_open_submission_identity_fk")
        || detail.contains("opportunity_open_submission_unique")) {
      return new SubmissionAlreadyOpenException();
    }
    return ex;
  }
}
