package br.com.segsense.infrastructure.consent;

import br.com.segsense.application.consent.ConsentNoticeRepository;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.consent.ConsentNotice;
import br.com.segsense.domain.consent.ConsentNoticeContent;
import br.com.segsense.domain.consent.ConsentNoticeField;
import br.com.segsense.domain.consent.ConsentNoticeSnapshot;
import br.com.segsense.domain.consent.ConsentNoticeStatus;
import br.com.segsense.domain.consent.NoticeAdministrativeDecision;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.FieldClassification;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Repository;

@Repository
public class JpaConsentNoticeRepository implements ConsentNoticeRepository {

  private final ConsentNoticeSpringRepository notices;
  private final ConsentNoticeSnapshotSpringRepository snapshots;
  private final ConsentNoticeFieldSpringRepository fields;
  private final ConsentNoticeDecisionSpringRepository decisions;

  public JpaConsentNoticeRepository(
      ConsentNoticeSpringRepository notices,
      ConsentNoticeSnapshotSpringRepository snapshots,
      ConsentNoticeFieldSpringRepository fields,
      ConsentNoticeDecisionSpringRepository decisions) {
    this.notices = notices;
    this.snapshots = snapshots;
    this.fields = fields;
    this.decisions = decisions;
  }

  @Override
  public ConsentNotice saveNew(ConsentNotice notice) {
    ConsentNoticeJpaEntity entity = new ConsentNoticeJpaEntity();
    copy(entity, notice);
    try {
      notices.saveAndFlush(entity);
      persistMissingSnapshots(notice, Set.of());
      notices.flush();
      snapshots.flush();
      fields.flush();
      return loadRequired(notice.id());
    } catch (DataIntegrityViolationException exception) {
      throw duplicateOrRethrow(exception);
    }
  }

  @Override
  public ConsentNotice saveSnapshot(ConsentNotice notice) {
    ConsentNoticeJpaEntity entity =
        notices.findById(notice.id()).orElseThrow(ResourceNotFoundException::new);
    Set<UUID> existing =
        snapshots.findByNoticeIdOrderByVersionNumberAsc(notice.id()).stream()
            .map(ConsentNoticeSnapshotJpaEntity::getId)
            .collect(Collectors.toSet());
    copy(entity, notice);
    try {
      notices.saveAndFlush(entity);
      persistMissingSnapshots(notice, existing);
      return loadRequired(notice.id());
    } catch (DataIntegrityViolationException exception) {
      throw duplicateOrRethrow(exception);
    }
  }

  @Override
  public ConsentNotice saveStatus(ConsentNotice notice) {
    ConsentNoticeJpaEntity entity =
        notices.findById(notice.id()).orElseThrow(ResourceNotFoundException::new);
    copy(entity, notice);
    notices.saveAndFlush(entity);
    persistDecision(notice);
    return loadRequired(notice.id());
  }

  @Override
  public Optional<ConsentNotice> findByScope(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId) {
    return notices
        .findByPublisherIdAndChannelIdAndEnvironmentIdAndOpportunityId(
            publisherId, channelId, environmentId, opportunityId)
        .map(this::toDomain);
  }

  @Override
  public Optional<ConsentNotice> findApprovedByOpportunityRevisionId(UUID opportunityRevisionId) {
    return notices
        .findByOpportunityRevisionIdAndStatus(opportunityRevisionId, ConsentNoticeStatus.APPROVED.name())
        .map(this::toDomain);
  }

  private void persistMissingSnapshots(ConsentNotice notice, Set<UUID> existingIds) {
    for (ConsentNoticeSnapshot snapshot : notice.snapshots()) {
      if (existingIds.contains(snapshot.id())) {
        continue;
      }
      snapshots.save(toSnapshotEntity(notice, snapshot));
      for (ConsentNoticeField field : snapshot.fields()) {
        fields.save(toFieldEntity(snapshot.id(), field));
      }
    }
  }

  private ConsentNotice loadRequired(UUID id) {
    return toDomain(notices.findById(id).orElseThrow(ResourceNotFoundException::new));
  }

  private ConsentNotice toDomain(ConsentNoticeJpaEntity entity) {
    List<ConsentNoticeSnapshot> restored = new ArrayList<>();
    for (ConsentNoticeSnapshotJpaEntity snapshot :
        snapshots.findByNoticeIdOrderByVersionNumberAsc(entity.getId())) {
      List<ConsentNoticeField> snapshotFields = new ArrayList<>();
      for (ConsentNoticeFieldJpaEntity field :
          fields.findBySnapshotIdOrderByPositionAsc(snapshot.getId())) {
        snapshotFields.add(
            ConsentNoticeField.restore(
                field.getId(),
                field.getOpportunityRevisionId(),
                field.getFieldKey(),
                field.getFieldLabel(),
                ContextFieldType.valueOf(field.getFieldType()),
                ContextFieldSource.valueOf(field.getFieldSource()),
                FieldClassification.valueOf(field.getClassification()),
                field.isRequired(),
                field.getPosition(),
                field.getAllowedValues() == null
                    ? List.of()
                    : Arrays.asList(field.getAllowedValues())));
      }
      restored.add(
          ConsentNoticeSnapshot.restore(
              snapshot.getId(),
              snapshot.getVersionNumber(),
              ConsentNoticeContent.parse(
                  snapshot.getPurposeTitle(),
                  snapshot.getPurposeDescription(),
                  snapshot.getTransparencyText(),
                  snapshot.getNoExternalSharingText()),
              snapshot.getContentHash(),
              snapshot.getCreatedAt(),
              snapshot.getCreatedBy(),
              snapshotFields));
    }
    return ConsentNotice.restore(
        entity.getId(),
        entity.getPublisherId(),
        entity.getChannelId(),
        entity.getEnvironmentId(),
        entity.getOpportunityId(),
        entity.getRevisionNumber(),
        entity.getOpportunityRevisionId(),
        entity.getCurrentVersion(),
        entity.getApprovedVersion(),
        ConsentNoticeStatus.valueOf(entity.getStatus()),
        entity.getVersion() == null ? 0L : entity.getVersion(),
        entity.getCreatedAt(),
        entity.getUpdatedAt(),
        entity.getCreatedBy(),
        entity.getUpdatedBy(),
        restored);
  }

  private static void copy(ConsentNoticeJpaEntity entity, ConsentNotice notice) {
    entity.setId(notice.id());
    entity.setPublisherId(notice.publisherId());
    entity.setChannelId(notice.channelId());
    entity.setEnvironmentId(notice.environmentId());
    entity.setOpportunityId(notice.opportunityId());
    entity.setRevisionNumber(notice.revisionNumber());
    entity.setOpportunityRevisionId(notice.opportunityRevisionId());
    entity.setCurrentVersion(notice.currentVersion());
    entity.setApprovedVersion(notice.approvedVersion());
    entity.setStatus(notice.status().name());
    entity.setCreatedAt(notice.createdAt());
    entity.setUpdatedAt(notice.updatedAt());
    entity.setCreatedBy(notice.createdBy());
    entity.setUpdatedBy(notice.updatedBy());
  }

  private void persistDecision(ConsentNotice notice) {
    NoticeAdministrativeDecision decision = notice.lastDecision();
    if (decision == null) {
      return;
    }
    ConsentNoticeDecisionJpaEntity entity = new ConsentNoticeDecisionJpaEntity();
    entity.setId(decision.id());
    entity.setNoticeId(decision.noticeId());
    entity.setNoticeVersion(decision.noticeVersion());
    entity.setContentHash(decision.contentHash());
    entity.setDecisionType(decision.decisionType());
    entity.setJustification(decision.justification());
    entity.setActor(decision.actor());
    entity.setOccurredAt(decision.occurredAt());
    decisions.saveAndFlush(entity);
  }

  private static ConsentNoticeSnapshotJpaEntity toSnapshotEntity(
      ConsentNotice notice, ConsentNoticeSnapshot snapshot) {
    ConsentNoticeSnapshotJpaEntity entity = new ConsentNoticeSnapshotJpaEntity();
    entity.setId(snapshot.id());
    entity.setNoticeId(notice.id());
    entity.setVersionNumber(snapshot.versionNumber());
    entity.setPurposeTitle(snapshot.content().purposeTitle());
    entity.setPurposeDescription(snapshot.content().purposeDescription());
    entity.setTransparencyText(snapshot.content().transparencyText());
    entity.setNoExternalSharingText(snapshot.content().noExternalSharingText());
    entity.setContentHash(snapshot.contentHash());
    entity.setCreatedAt(snapshot.createdAt());
    entity.setCreatedBy(snapshot.createdBy());
    entity.setOpportunityRevisionId(notice.opportunityRevisionId());
    return entity;
  }

  private static ConsentNoticeFieldJpaEntity toFieldEntity(UUID snapshotId, ConsentNoticeField field) {
    ConsentNoticeFieldJpaEntity entity = new ConsentNoticeFieldJpaEntity();
    entity.setId(field.id());
    entity.setSnapshotId(snapshotId);
    entity.setOpportunityRevisionId(field.opportunityRevisionId());
    entity.setFieldKey(field.fieldKey());
    entity.setFieldLabel(field.label());
    entity.setFieldType(field.fieldType().name());
    entity.setFieldSource(field.fieldSource().name());
    entity.setClassification(field.classification().name());
    entity.setRequired(field.required());
    entity.setPosition(field.position());
    entity.setAllowedValues(
        field.allowedValues().isEmpty() ? null : field.allowedValues().toArray(String[]::new));
    return entity;
  }

  private static RuntimeException duplicateOrRethrow(DataIntegrityViolationException exception) {
    String detail = String.valueOf(exception.getMostSpecificCause().getMessage());
    if (detail.contains("consent_notice_revision_unique")) {
      return new DuplicateResourceKeyException(
          "CONSENT_NOTICE_CONFLICT",
          "Já existe um aviso de finalidade para esta revisão aprovada.");
    }
    return exception;
  }
}
