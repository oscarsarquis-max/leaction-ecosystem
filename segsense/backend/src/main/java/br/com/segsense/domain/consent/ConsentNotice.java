package br.com.segsense.domain.consent;

import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.catalog.InvalidStateTransitionException;
import br.com.segsense.domain.catalog.OptimisticConcurrencyException;
import br.com.segsense.domain.opportunity.AdministrativeJustification;
import br.com.segsense.domain.opportunity.ContextFieldDefinition;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

public final class ConsentNotice {

  private final UUID id;
  private final UUID publisherId;
  private final UUID channelId;
  private final UUID environmentId;
  private final UUID opportunityId;
  private final int revisionNumber;
  private final UUID opportunityRevisionId;
  private int currentVersion;
  private Integer approvedVersion;
  private ConsentNoticeStatus status;
  private final long version;
  private final Instant createdAt;
  private Instant updatedAt;
  private final String createdBy;
  private String updatedBy;
  private final List<ConsentNoticeSnapshot> snapshots;
  private NoticeAdministrativeDecision lastDecision;

  private ConsentNotice(
      UUID id,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      int revisionNumber,
      UUID opportunityRevisionId,
      int currentVersion,
      Integer approvedVersion,
      ConsentNoticeStatus status,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy,
      List<ConsentNoticeSnapshot> snapshots) {
    this.id = id;
    this.publisherId = publisherId;
    this.channelId = channelId;
    this.environmentId = environmentId;
    this.opportunityId = opportunityId;
    this.revisionNumber = revisionNumber;
    this.opportunityRevisionId = opportunityRevisionId;
    this.currentVersion = currentVersion;
    this.approvedVersion = approvedVersion;
    this.status = status;
    this.version = version;
    this.createdAt = createdAt;
    this.updatedAt = updatedAt;
    this.createdBy = createdBy;
    this.updatedBy = updatedBy;
    this.snapshots = new ArrayList<>(snapshots);
  }

  public static ConsentNotice create(
      UUID id,
      ContextualOpportunity opportunity,
      ConsentNoticeContent content,
      Instant now,
      String actor) {
    Objects.requireNonNull(opportunity, "opportunity");
    if (opportunity.approvedRevision() == null
        || opportunity.current().revisionNumber() != opportunity.approvedRevision()) {
      throw new CatalogValidationException(
          "O aviso de finalidade só pode ser criado na revisão aprovada.");
    }
    UUID revisionId = opportunity.current().id();
    List<ConsentNoticeField> fields = coveredFields(revisionId, opportunity.current().content().contextFields());
    ConsentNoticeSnapshot snapshot =
        ConsentNoticeSnapshot.create(UUID.randomUUID(), 1, content, now, actor, fields);
    return new ConsentNotice(
        Objects.requireNonNull(id, "id"),
        opportunity.publisherId(),
        opportunity.channelId(),
        opportunity.environmentId(),
        opportunity.id(),
        opportunity.approvedRevision(),
        revisionId,
        1,
        null,
        ConsentNoticeStatus.DRAFT,
        0L,
        now,
        now,
        actor,
        actor,
        List.of(snapshot));
  }

  public static ConsentNotice restore(
      UUID id,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      int revisionNumber,
      UUID opportunityRevisionId,
      int currentVersion,
      Integer approvedVersion,
      ConsentNoticeStatus status,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy,
      List<ConsentNoticeSnapshot> snapshots) {
    return new ConsentNotice(
        id,
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        revisionNumber,
        opportunityRevisionId,
        currentVersion,
        approvedVersion,
        status,
        version,
        createdAt,
        updatedAt,
        createdBy,
        updatedBy,
        snapshots);
  }

  public void editDraft(
      ConsentNoticeContent content,
      ContextualOpportunity opportunity,
      long expectedVersion,
      Instant now,
      String actor) {
    requireExpected(expectedVersion);
    requireDraft();
    UUID revisionId = opportunityRevisionId;
    List<ConsentNoticeField> fields =
        coveredFields(revisionId, opportunity.current().content().contextFields());
    currentVersion = currentVersion + 1;
    snapshots.add(
        ConsentNoticeSnapshot.create(UUID.randomUUID(), currentVersion, content, now, actor, fields));
    updatedAt = now;
    updatedBy = actor;
  }

  public void approve(
      AdministrativeJustification justification, long expectedVersion, Instant now, String actor) {
    Objects.requireNonNull(justification, "justification");
    requireExpected(expectedVersion);
    requireDraft();
    status = ConsentNoticeStatus.APPROVED;
    approvedVersion = currentVersion;
    updatedAt = now;
    updatedBy = actor;
    lastDecision = recordDecision("APPROVED", justification.value(), actor, now);
  }

  public void retire(AdministrativeJustification justification, long expectedVersion, Instant now, String actor) {
    Objects.requireNonNull(justification, "justification");
    requireExpected(expectedVersion);
    if (status != ConsentNoticeStatus.APPROVED) {
      throw new InvalidStateTransitionException();
    }
    status = ConsentNoticeStatus.RETIRED;
    updatedAt = now;
    updatedBy = actor;
    lastDecision = recordDecision("RETIRED", justification.value(), actor, now);
  }

  private NoticeAdministrativeDecision recordDecision(
      String decisionType, String justification, String actor, Instant now) {
    ConsentNoticeSnapshot snapshot = currentSnapshot();
    return new NoticeAdministrativeDecision(
        UUID.randomUUID(),
        id,
        snapshot.versionNumber(),
        snapshot.contentHash(),
        decisionType,
        justification,
        actor,
        now);
  }

  public NoticeAdministrativeDecision lastDecision() {
    return lastDecision;
  }

  public ConsentNoticeSnapshot currentSnapshot() {
    return snapshots.stream()
        .filter(snapshot -> snapshot.versionNumber() == currentVersion)
        .findFirst()
        .orElseThrow(ConsentNoticeNotFoundException::new);
  }

  public ConsentNoticeSnapshot approvedSnapshot() {
    if (approvedVersion == null) {
      throw new ConsentNoticeNotApprovedException();
    }
    return snapshots.stream()
        .filter(snapshot -> snapshot.versionNumber() == approvedVersion)
        .findFirst()
        .orElseThrow(ConsentNoticeNotApprovedException::new);
  }

  public boolean effectivelyApproved() {
    return status == ConsentNoticeStatus.APPROVED;
  }

  public void requireApprovedForNewInstance() {
    if (status != ConsentNoticeStatus.APPROVED) {
      throw new ConsentNoticeNotApprovedException();
    }
  }

  private void requireDraft() {
    if (status != ConsentNoticeStatus.DRAFT) {
      throw new InvalidStateTransitionException();
    }
  }

  private void requireExpected(long expectedVersion) {
    if (expectedVersion != version) {
      throw new OptimisticConcurrencyException();
    }
  }

  static List<ConsentNoticeField> coveredFields(
      UUID opportunityRevisionId, List<ContextFieldDefinition> definitions) {
    List<ConsentNoticeField> fields = new ArrayList<>();
    for (ContextFieldDefinition definition : definitions) {
      if (definition.source() == ContextFieldSource.USER
          || definition.source() == ContextFieldSource.EITHER) {
        fields.add(ConsentNoticeField.fromDefinition(UUID.randomUUID(), opportunityRevisionId, definition));
      }
    }
    return List.copyOf(fields);
  }

  public UUID id() {
    return id;
  }

  public UUID publisherId() {
    return publisherId;
  }

  public UUID channelId() {
    return channelId;
  }

  public UUID environmentId() {
    return environmentId;
  }

  public UUID opportunityId() {
    return opportunityId;
  }

  public int revisionNumber() {
    return revisionNumber;
  }

  public UUID opportunityRevisionId() {
    return opportunityRevisionId;
  }

  public int currentVersion() {
    return currentVersion;
  }

  public Integer approvedVersion() {
    return approvedVersion;
  }

  public ConsentNoticeStatus status() {
    return status;
  }

  public long version() {
    return version;
  }

  public Instant createdAt() {
    return createdAt;
  }

  public Instant updatedAt() {
    return updatedAt;
  }

  public String createdBy() {
    return createdBy;
  }

  public String updatedBy() {
    return updatedBy;
  }

  public List<ConsentNoticeSnapshot> snapshots() {
    return List.copyOf(snapshots);
  }
}
