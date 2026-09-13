package br.com.segsense.infrastructure.consent;

import br.com.segsense.application.consent.ContextInstanceRepository;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.consent.CollectedFieldValue;
import br.com.segsense.domain.consent.ConsentDecision;
import br.com.segsense.domain.consent.ConsentNoticeField;
import br.com.segsense.domain.consent.ContextInstance;
import br.com.segsense.domain.consent.ContextInstanceStatus;
import br.com.segsense.domain.consent.InstanceCredentialNotReplayableException;
import org.springframework.dao.DataIntegrityViolationException;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.FieldClassification;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class JpaContextInstanceRepository implements ContextInstanceRepository {

  private final ContextInstanceSpringRepository instances;
  private final ContextInstanceValueSpringRepository values;
  private final ConsentDecisionSpringRepository decisions;
  private final ConsentNoticeFieldSpringRepository noticeFields;
  private final JdbcTemplate jdbcTemplate;

  public JpaContextInstanceRepository(
      ContextInstanceSpringRepository instances,
      ContextInstanceValueSpringRepository values,
      ConsentDecisionSpringRepository decisions,
      ConsentNoticeFieldSpringRepository noticeFields,
      JdbcTemplate jdbcTemplate) {
    this.instances = instances;
    this.values = values;
    this.decisions = decisions;
    this.noticeFields = noticeFields;
    this.jdbcTemplate = jdbcTemplate;
  }

  @Override
  public ContextInstance saveNew(ContextInstance instance) {
    ContextInstanceJpaEntity entity = new ContextInstanceJpaEntity();
    copy(entity, instance);
    try {
      instances.saveAndFlush(entity);
      replaceValues(instance);
      return loadRequired(instance.id());
    } catch (DataIntegrityViolationException exception) {
      String detail = String.valueOf(exception.getMostSpecificCause().getMessage());
      if (detail.contains("context_instance_idempotency_unique")) {
        throw new InstanceCredentialNotReplayableException();
      }
      throw exception;
    }
  }

  @Override
  public ContextInstance saveValues(ContextInstance instance) {
    ContextInstanceJpaEntity entity =
        instances.findById(instance.id()).orElseThrow(ResourceNotFoundException::new);
    copyMutable(entity, instance);
    instances.saveAndFlush(entity);
    replaceValues(instance);
    return loadRequired(instance.id());
  }

  @Override
  public ContextInstance saveDecision(ContextInstance instance, ConsentDecision decision) {
    ContextInstanceJpaEntity entity =
        instances.findById(instance.id()).orElseThrow(ResourceNotFoundException::new);
    copyMutable(entity, instance);
    instances.saveAndFlush(entity);
    if (decision != null) {
      decisions.saveAndFlush(toDecisionEntity(decision));
    }
    return loadRequired(instance.id());
  }

  @Override
  public Optional<ContextInstance> findByCredentialDigest(byte[] digest) {
    return instances.findByCredentialDigest(digest).map(this::toDomain);
  }

  @Override
  public Optional<ContextInstance> findByIdempotencyKeyDigest(byte[] digest) {
    return instances.findByIdempotencyKeyDigest(digest).map(this::toDomain);
  }

  private void replaceValues(ContextInstance instance) {
    values.deleteByInstanceId(instance.id());
    values.flush();
    for (CollectedFieldValue value : instance.values()) {
      values.save(toValueEntity(instance, value));
    }
    values.flush();
  }

  private ContextInstance loadRequired(UUID id) {
    return toDomain(instances.findById(id).orElseThrow(ResourceNotFoundException::new));
  }

  private ContextInstance toDomain(ContextInstanceJpaEntity entity) {
    List<ConsentNoticeField> collectible = collectibleFields(entity);
    List<CollectedFieldValue> restoredValues = new ArrayList<>();
    for (ContextInstanceValueJpaEntity value :
        values.findByInstanceIdOrderByFieldKeyAsc(entity.getId())) {
      restoredValues.add(
          CollectedFieldValue.restore(
              value.getId(),
              value.getFieldKey(),
              ContextFieldType.valueOf(value.getFieldType()),
              ContextFieldSource.valueOf(value.getFieldSource()),
              FieldClassification.valueOf(value.getClassification()),
              value.getTextValue(),
              value.getNumberValue(),
              value.getBooleanValue(),
              value.getDateValue()));
    }
    return ContextInstance.restore(
        entity.getId(),
        entity.getLinkId(),
        entity.getPublisherId(),
        entity.getChannelId(),
        entity.getEnvironmentId(),
        entity.getOpportunityId(),
        entity.getRevisionNumber(),
        entity.getOpportunityRevisionId(),
        entity.getNoticeId(),
        entity.getNoticeVersion(),
        entity.getNoticeSnapshotId(),
        entity.getNoticeContentHash(),
        entity.getCredentialDigest(),
        entity.getCredentialHint(),
        entity.getIdempotencyKeyDigest(),
        ContextInstanceStatus.valueOf(entity.getStatus()),
        entity.isValuesUnavailable(),
        entity.getExpiresAt(),
        entity.getCreatedAt(),
        entity.getUpdatedAt(),
        entity.getVersion() == null ? 0L : entity.getVersion(),
        entity.getCreatedCorrelationId(),
        restoredValues,
        collectible);
  }

  private List<ConsentNoticeField> collectibleFields(ContextInstanceJpaEntity entity) {
    Set<String> publisherBound = new HashSet<>(publisherBoundKeys(entity.getLinkId()));
    List<ConsentNoticeField> collectible = new ArrayList<>();
    for (ConsentNoticeFieldJpaEntity field :
        noticeFields.findBySnapshotIdOrderByPositionAsc(entity.getNoticeSnapshotId())) {
      ContextFieldSource source = ContextFieldSource.valueOf(field.getFieldSource());
      if (source == ContextFieldSource.USER
          || (source == ContextFieldSource.EITHER && !publisherBound.contains(field.getFieldKey()))) {
        collectible.add(
            ConsentNoticeField.restore(
                field.getId(),
                field.getOpportunityRevisionId(),
                field.getFieldKey(),
                field.getFieldLabel(),
                ContextFieldType.valueOf(field.getFieldType()),
                source,
                FieldClassification.valueOf(field.getClassification()),
                field.isRequired(),
                field.getPosition(),
                field.getAllowedValues() == null
                    ? List.of()
                    : Arrays.asList(field.getAllowedValues())));
      }
    }
    return collectible;
  }

  private List<String> publisherBoundKeys(UUID linkId) {
    return jdbcTemplate.queryForList(
        "SELECT field_key FROM segsense.published_context_link_binding WHERE link_id = ?",
        String.class,
        linkId);
  }

  private static void copy(ContextInstanceJpaEntity entity, ContextInstance instance) {
    entity.setId(instance.id());
    entity.setLinkId(instance.linkId());
    entity.setPublisherId(instance.publisherId());
    entity.setChannelId(instance.channelId());
    entity.setEnvironmentId(instance.environmentId());
    entity.setOpportunityId(instance.opportunityId());
    entity.setRevisionNumber(instance.revisionNumber());
    entity.setOpportunityRevisionId(instance.opportunityRevisionId());
    entity.setNoticeId(instance.noticeId());
    entity.setNoticeVersion(instance.noticeVersion());
    entity.setNoticeSnapshotId(instance.noticeSnapshotId());
    entity.setNoticeContentHash(instance.noticeContentHash());
    entity.setCredentialDigest(instance.credentialDigest());
    entity.setCredentialHint(instance.credentialHint());
    entity.setIdempotencyKeyDigest(instance.idempotencyKeyDigest());
    entity.setCreatedAt(instance.createdAt());
    entity.setCreatedCorrelationId(instance.createdCorrelationId());
    copyMutable(entity, instance);
  }

  private static void copyMutable(ContextInstanceJpaEntity entity, ContextInstance instance) {
    entity.setStatus(instance.status().name());
    entity.setValuesUnavailable(instance.valuesUnavailable());
    entity.setExpiresAt(instance.expiresAt());
    entity.setUpdatedAt(instance.updatedAt());
  }

  private static ContextInstanceValueJpaEntity toValueEntity(
      ContextInstance instance, CollectedFieldValue value) {
    ContextInstanceValueJpaEntity entity = new ContextInstanceValueJpaEntity();
    entity.setId(value.id());
    entity.setInstanceId(instance.id());
    entity.setSnapshotId(instance.noticeSnapshotId());
    entity.setFieldKey(value.fieldKey());
    entity.setFieldType(value.fieldType().name());
    entity.setFieldSource(value.fieldSource().name());
    entity.setClassification(value.classification().name());
    entity.setTextValue(value.textValue());
    entity.setNumberValue(value.numberValue());
    entity.setBooleanValue(value.booleanValue());
    entity.setDateValue(value.dateValue());
    entity.setOpportunityRevisionId(instance.opportunityRevisionId());
    return entity;
  }

  private static ConsentDecisionJpaEntity toDecisionEntity(ConsentDecision decision) {
    ConsentDecisionJpaEntity entity = new ConsentDecisionJpaEntity();
    entity.setId(decision.id());
    entity.setInstanceId(decision.instanceId());
    entity.setDecisionType(decision.decisionType().name());
    entity.setNoticeVersion(decision.noticeVersion());
    entity.setNoticeContentHash(decision.noticeContentHash());
    entity.setCoveredFieldsHash(decision.coveredFieldsHash());
    entity.setOccurredAt(decision.occurredAt());
    entity.setCorrelationId(decision.correlationId());
    entity.setInstanceVersionBefore(decision.instanceVersionBefore());
    entity.setInstanceVersionAfter(decision.instanceVersionAfter());
    entity.setActor(decision.actor());
    return entity;
  }
}
