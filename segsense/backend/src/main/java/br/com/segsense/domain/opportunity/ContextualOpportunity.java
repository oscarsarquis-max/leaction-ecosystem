package br.com.segsense.domain.opportunity;

import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.OptimisticConcurrencyException;
import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public final class ContextualOpportunity {

  private final UUID id;
  private final UUID publisherId;
  private final UUID channelId;
  private final UUID environmentId;
  private final ResourceKey key;
  private OpportunityStatus status;
  private int currentRevision;
  private final long version;
  private final Instant createdAt;
  private Instant updatedAt;
  private final String createdBy;
  private String updatedBy;
  private OpportunityRevision current;
  private Integer submittedRevision;
  private Integer approvedRevision;
  private UUID openSubmissionId;
  private String submittedBy;
  private String approvedBy;

  private ContextualOpportunity(
      UUID id,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      ResourceKey key,
      OpportunityStatus status,
      int currentRevision,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy,
      OpportunityRevision current,
      Integer submittedRevision,
      Integer approvedRevision,
      UUID openSubmissionId,
      String submittedBy,
      String approvedBy) {
    this.id = Objects.requireNonNull(id, "id");
    this.publisherId = Objects.requireNonNull(publisherId, "publisherId");
    this.channelId = Objects.requireNonNull(channelId, "channelId");
    this.environmentId = Objects.requireNonNull(environmentId, "environmentId");
    this.key = Objects.requireNonNull(key, "key");
    this.status = Objects.requireNonNull(status, "status");
    this.currentRevision = currentRevision;
    this.version = version;
    this.createdAt = Objects.requireNonNull(createdAt, "createdAt");
    this.updatedAt = Objects.requireNonNull(updatedAt, "updatedAt");
    this.createdBy = requireSubject(createdBy);
    this.updatedBy = requireSubject(updatedBy);
    this.current = Objects.requireNonNull(current, "current");
    this.submittedRevision = submittedRevision;
    this.approvedRevision = approvedRevision;
    this.openSubmissionId = openSubmissionId;
    this.submittedBy = submittedBy;
    this.approvedBy = approvedBy;
  }

  public static ContextualOpportunity create(
      UUID id,
      Publisher publisher,
      Channel channel,
      ContextualEnvironment environment,
      ResourceKey key,
      OpportunityContent content,
      Instant now,
      String actorSubject) {
    Objects.requireNonNull(publisher, "publisher");
    Objects.requireNonNull(channel, "channel");
    Objects.requireNonNull(environment, "environment");
    if (!channel.publisherId().equals(publisher.id())
        || !environment.publisherId().equals(publisher.id())
        || !environment.channelId().equals(channel.id())) {
      throw new ResourceNotFoundException();
    }
    if (!environment.effectivelyAvailable(publisher, channel)) {
      throw new InvalidParentStateException();
    }
    String subject = requireSubject(actorSubject);
    Instant timestamp = Objects.requireNonNull(now, "now");
    OpportunityRevision revision =
        new OpportunityRevision(UUID.randomUUID(), 1, content, timestamp, subject);
    return new ContextualOpportunity(
        id,
        publisher.id(),
        channel.id(),
        environment.id(),
        key,
        OpportunityStatus.DRAFT,
        1,
        0L,
        timestamp,
        timestamp,
        subject,
        subject,
        revision,
        null,
        null,
        null,
        null,
        null);
  }

  public static ContextualOpportunity restore(
      UUID id,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      ResourceKey key,
      OpportunityStatus status,
      int currentRevision,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy,
      OpportunityRevision current,
      Integer submittedRevision,
      Integer approvedRevision,
      UUID openSubmissionId,
      String submittedBy,
      String approvedBy) {
    return new ContextualOpportunity(
        id,
        publisherId,
        channelId,
        environmentId,
        key,
        status,
        currentRevision,
        version,
        createdAt,
        updatedAt,
        createdBy,
        updatedBy,
        current,
        submittedRevision,
        approvedRevision,
        openSubmissionId,
        submittedBy,
        approvedBy);
  }

  public OpportunityRevision revise(
      long expectedVersion,
      int baseRevision,
      OpportunityContent content,
      Instant now,
      String actor) {
    requireExpectedVersion(expectedVersion);
    if (status != OpportunityStatus.DRAFT) {
      throw new InvalidGovernanceTransitionException();
    }
    if (baseRevision != currentRevision) {
      throw new StaleOpportunityRevisionException();
    }
    if (current.content().sameAs(content)) {
      throw new NoContentChangeException();
    }
    int next = currentRevision + 1;
    OpportunityRevision revision =
        new OpportunityRevision(UUID.randomUUID(), next, content, now, requireSubject(actor));
    this.currentRevision = next;
    this.current = revision;
    touch(now, actor);
    return revision;
  }

  public GovernanceEffect submit(long expectedVersion, Instant now, String actor, UUID correlationId) {
    requireExpectedVersion(expectedVersion);
    if (status != OpportunityStatus.DRAFT) {
      throw new InvalidGovernanceTransitionException();
    }
    if (openSubmissionId != null) {
      throw new SubmissionAlreadyOpenException();
    }
    String subject = requireSubject(actor);
    UUID submissionId = UUID.randomUUID();
    OpportunityStatus previous = status;
    status = OpportunityStatus.UNDER_REVIEW;
    submittedRevision = currentRevision;
    openSubmissionId = submissionId;
    submittedBy = subject;
    touch(now, subject);
    OpportunitySubmission submission =
        new OpportunitySubmission(
            submissionId,
            id,
            currentRevision,
            now,
            subject,
            requireCorrelation(correlationId),
            SubmissionStatus.OPEN);
    return new GovernanceEffect(
        event(LifecycleEventType.SUBMITTED, previous, status, now, subject, null, correlationId),
        submission,
        null);
  }

  public GovernanceEffect returnForChanges(
      long expectedVersion,
      int revisionNumber,
      String justification,
      Instant now,
      String actor,
      UUID correlationId) {
    requireReviewCommand(expectedVersion, revisionNumber, actor);
    AdministrativeJustification text = AdministrativeJustification.required(justification);
    OpportunityStatus previous = status;
    OpportunitySubmission closed = closeOpenSubmission();
    OpportunityDecision decision =
        decision(closed, DecisionOutcome.RETURNED, now, actor, text.value(), correlationId);
    status = OpportunityStatus.DRAFT;
    submittedRevision = null;
    openSubmissionId = null;
    submittedBy = null;
    touch(now, actor);
    return new GovernanceEffect(
        event(
            LifecycleEventType.RETURNED,
            previous,
            status,
            now,
            actor,
            text.value(),
            correlationId),
        closed,
        decision);
  }

  public GovernanceEffect approve(
      long expectedVersion, int revisionNumber, Instant now, String actor, UUID correlationId) {
    requireReviewCommand(expectedVersion, revisionNumber, actor);
    OpportunityStatus previous = status;
    OpportunitySubmission closed = closeOpenSubmission();
    OpportunityDecision decision =
        decision(closed, DecisionOutcome.APPROVED, now, actor, null, correlationId);
    status = OpportunityStatus.APPROVED;
    approvedRevision = submittedRevision;
    approvedBy = requireSubject(actor);
    openSubmissionId = null;
    touch(now, actor);
    return new GovernanceEffect(
        event(LifecycleEventType.APPROVED, previous, status, now, actor, null, correlationId),
        closed,
        decision);
  }

  public GovernanceEffect reject(
      long expectedVersion,
      int revisionNumber,
      String justification,
      Instant now,
      String actor,
      UUID correlationId) {
    requireReviewCommand(expectedVersion, revisionNumber, actor);
    AdministrativeJustification text = AdministrativeJustification.required(justification);
    OpportunityStatus previous = status;
    OpportunitySubmission closed = closeOpenSubmission();
    OpportunityDecision decision =
        decision(closed, DecisionOutcome.REJECTED, now, actor, text.value(), correlationId);
    status = OpportunityStatus.REVOKED;
    openSubmissionId = null;
    touch(now, actor);
    return new GovernanceEffect(
        event(
            LifecycleEventType.REJECTED, previous, status, now, actor, text.value(), correlationId),
        closed,
        decision);
  }

  public GovernanceEffect activatePublication(
      long expectedVersion,
      Instant now,
      String actor,
      UUID correlationId,
      Publisher publisher,
      Channel channel,
      ContextualEnvironment environment) {
    requireExpectedVersion(expectedVersion);
    if (status != OpportunityStatus.APPROVED) {
      throw new InvalidGovernanceTransitionException();
    }
    if (approvedRevision == null || approvedRevision != currentRevision) {
      throw new RevisionNotCurrentException();
    }
    requireDistinct(actor, approvedBy);
    requirePublishable(publisher, channel, environment, now);
    OpportunityStatus previous = status;
    status = OpportunityStatus.PUBLISHED;
    touch(now, actor);
    return effectOnly(
        event(LifecycleEventType.ACTIVATED, previous, status, now, actor, null, correlationId));
  }

  public GovernanceEffect pause(long expectedVersion, Instant now, String actor, UUID correlationId) {
    requireExpectedVersion(expectedVersion);
    if (status != OpportunityStatus.PUBLISHED) {
      throw new InvalidGovernanceTransitionException();
    }
    OpportunityStatus previous = status;
    status = OpportunityStatus.PAUSED;
    touch(now, actor);
    return effectOnly(
        event(LifecycleEventType.PAUSED, previous, status, now, actor, null, correlationId));
  }

  public GovernanceEffect resume(
      long expectedVersion,
      Instant now,
      String actor,
      UUID correlationId,
      Publisher publisher,
      Channel channel,
      ContextualEnvironment environment) {
    requireExpectedVersion(expectedVersion);
    if (status != OpportunityStatus.PAUSED) {
      throw new InvalidGovernanceTransitionException();
    }
    requirePublishable(publisher, channel, environment, now);
    OpportunityStatus previous = status;
    status = OpportunityStatus.PUBLISHED;
    touch(now, actor);
    return effectOnly(
        event(LifecycleEventType.RESUMED, previous, status, now, actor, null, correlationId));
  }

  public GovernanceEffect expire(long expectedVersion, Instant now, String actor, UUID correlationId) {
    requireExpectedVersion(expectedVersion);
    if (status != OpportunityStatus.PUBLISHED && status != OpportunityStatus.PAUSED) {
      throw new InvalidGovernanceTransitionException();
    }
    if (!PublicationWindow.isExpired(current.content(), now)) {
      throw new PublicationNotExpiredException();
    }
    OpportunityStatus previous = status;
    status = OpportunityStatus.EXPIRED;
    touch(now, actor);
    return effectOnly(
        event(LifecycleEventType.EXPIRED, previous, status, now, actor, null, correlationId));
  }

  public GovernanceEffect revoke(
      long expectedVersion, String justification, Instant now, String actor, UUID correlationId) {
    requireExpectedVersion(expectedVersion);
    if (status != OpportunityStatus.APPROVED
        && status != OpportunityStatus.PUBLISHED
        && status != OpportunityStatus.PAUSED) {
      throw new InvalidGovernanceTransitionException();
    }
    AdministrativeJustification text = AdministrativeJustification.required(justification);
    OpportunityStatus previous = status;
    status = OpportunityStatus.REVOKED;
    touch(now, actor);
    return effectOnly(
        event(LifecycleEventType.REVOKED, previous, status, now, actor, text.value(), correlationId));
  }

  public void requireExpectedVersion(long expectedVersion) {
    if (this.version != expectedVersion) {
      throw new OptimisticConcurrencyException();
    }
  }

  public boolean effectivelyAvailable(
      Publisher publisher, Channel channel, ContextualEnvironment environment) {
    return environment.effectivelyAvailable(publisher, channel);
  }

  public boolean effectivelyPublishable(
      Publisher publisher, Channel channel, ContextualEnvironment environment, Instant now) {
    return environment.effectivelyAvailable(publisher, channel)
        && PublicationWindow.isOpen(current.content(), now);
  }

  public boolean effectivelyPublished(
      Publisher publisher, Channel channel, ContextualEnvironment environment, Instant now) {
    return status == OpportunityStatus.PUBLISHED
        && effectivelyPublishable(publisher, channel, environment, now);
  }

  private void requireReviewCommand(long expectedVersion, int revisionNumber, String actor) {
    requireExpectedVersion(expectedVersion);
    if (status != OpportunityStatus.UNDER_REVIEW || openSubmissionId == null) {
      throw new InvalidGovernanceTransitionException();
    }
    if (submittedRevision == null || revisionNumber != submittedRevision) {
      throw new RevisionNotCurrentException();
    }
    requireDistinct(actor, current.createdBy());
    requireDistinct(actor, submittedBy);
  }

  private void requirePublishable(
      Publisher publisher, Channel channel, ContextualEnvironment environment, Instant now) {
    if (!environment.effectivelyAvailable(publisher, channel)) {
      throw new NotEffectivelyPublishableException();
    }
    if (!PublicationWindow.isOpen(current.content(), now)) {
      throw new PublicationWindowNotOpenException();
    }
  }

  private OpportunitySubmission closeOpenSubmission() {
    if (openSubmissionId == null || submittedRevision == null || submittedBy == null) {
      throw new InvalidGovernanceTransitionException();
    }
    return new OpportunitySubmission(
        openSubmissionId,
        id,
        submittedRevision,
        updatedAt,
        submittedBy,
        UUID.fromString("00000000-0000-4000-8000-000000000000"),
        SubmissionStatus.OPEN);
  }

  private OpportunityDecision decision(
      OpportunitySubmission submission,
      DecisionOutcome outcome,
      Instant now,
      String actor,
      String justification,
      UUID correlationId) {
    return new OpportunityDecision(
        UUID.randomUUID(),
        submission.id(),
        id,
        submission.revisionNumber(),
        outcome,
        now,
        requireSubject(actor),
        justification,
        requireCorrelation(correlationId));
  }

  private LifecycleEvent event(
      LifecycleEventType type,
      OpportunityStatus previous,
      OpportunityStatus next,
      Instant now,
      String actor,
      String justification,
      UUID correlationId) {
    return new LifecycleEvent(
        UUID.randomUUID(),
        id,
        currentRevision,
        type,
        previous,
        next,
        requireSubject(actor),
        now,
        justification,
        requireCorrelation(correlationId));
  }

  private static GovernanceEffect effectOnly(LifecycleEvent event) {
    return new GovernanceEffect(event, null, null);
  }

  private static void requireDistinct(String actor, String other) {
    if (other != null && requireSubject(actor).equals(other)) {
      throw new SegregationOfDutiesException();
    }
  }

  private static UUID requireCorrelation(UUID correlationId) {
    if (correlationId == null) {
      throw new CatalogValidationException("A correlação da solicitação é obrigatória.");
    }
    return correlationId;
  }

  private void touch(Instant now, String actorSubject) {
    this.updatedAt = Objects.requireNonNull(now, "now");
    this.updatedBy = requireSubject(actorSubject);
  }

  private static String requireSubject(String subject) {
    if (subject == null || subject.isBlank()) {
      throw new CatalogValidationException("A autoria técnica é obrigatória.");
    }
    String normalized = subject.trim();
    if (normalized.length() > 128) {
      throw new CatalogValidationException("A autoria técnica é inválida.");
    }
    return normalized;
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

  public ResourceKey key() {
    return key;
  }

  public OpportunityStatus status() {
    return status;
  }

  public int currentRevision() {
    return currentRevision;
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

  public OpportunityRevision current() {
    return current;
  }

  public Integer submittedRevision() {
    return submittedRevision;
  }

  public Integer approvedRevision() {
    return approvedRevision;
  }

  public UUID openSubmissionId() {
    return openSubmissionId;
  }

  public String submittedBy() {
    return submittedBy;
  }

  public String approvedBy() {
    return approvedBy;
  }
}
