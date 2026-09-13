package br.com.segsense.domain.demonstration;

import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.catalog.InvalidStateTransitionException;
import br.com.segsense.domain.catalog.OptimisticConcurrencyException;
import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.opportunity.AdministrativeJustification;
import br.com.segsense.domain.opportunity.SegregationOfDutiesException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

public final class DemonstrationStory {

  private final UUID id;
  private final ResourceKey key;
  private DemonstrationWorkflowStatus workflowStatus;
  private DemonstrationPublicationStatus publicationStatus;
  private int currentRevision;
  private Integer publishedRevision;
  private String submittedBy;
  private final long version;
  private final Instant createdAt;
  private Instant updatedAt;
  private final String createdBy;
  private String updatedBy;
  private DemonstrationRevision current;
  private final List<DemonstrationDecision> pendingDecisions = new ArrayList<>();

  private DemonstrationStory(
      UUID id,
      ResourceKey key,
      DemonstrationWorkflowStatus workflowStatus,
      DemonstrationPublicationStatus publicationStatus,
      int currentRevision,
      Integer publishedRevision,
      String submittedBy,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy,
      DemonstrationRevision current) {
    this.id = Objects.requireNonNull(id);
    this.key = Objects.requireNonNull(key);
    this.workflowStatus = Objects.requireNonNull(workflowStatus);
    this.publicationStatus = Objects.requireNonNull(publicationStatus);
    this.currentRevision = currentRevision;
    this.publishedRevision = publishedRevision;
    this.submittedBy = submittedBy;
    this.version = version;
    this.createdAt = Objects.requireNonNull(createdAt);
    this.updatedAt = Objects.requireNonNull(updatedAt);
    this.createdBy = requireSubject(createdBy);
    this.updatedBy = requireSubject(updatedBy);
    this.current = Objects.requireNonNull(current);
  }

  public static DemonstrationStory create(
      UUID id,
      ResourceKey key,
      DemonstrationRevisionContent content,
      Map<UUID, DemonstrationSource> sources,
      Instant now,
      String actor) {
    String subject = requireSubject(actor);
    Instant timestamp = Objects.requireNonNull(now);
    DemonstrationRevision revision =
        content.toRevision(UUID.randomUUID(), 1, false, timestamp, subject, sources);
    return new DemonstrationStory(
        id,
        key,
        DemonstrationWorkflowStatus.DRAFT,
        DemonstrationPublicationStatus.UNPUBLISHED,
        1,
        null,
        null,
        0L,
        timestamp,
        timestamp,
        subject,
        subject,
        revision);
  }

  public static DemonstrationStory restore(
      UUID id,
      ResourceKey key,
      DemonstrationWorkflowStatus workflowStatus,
      DemonstrationPublicationStatus publicationStatus,
      int currentRevision,
      Integer publishedRevision,
      String submittedBy,
      long version,
      Instant createdAt,
      Instant updatedAt,
      String createdBy,
      String updatedBy,
      DemonstrationRevision current) {
    return new DemonstrationStory(
        id,
        key,
        workflowStatus,
        publicationStatus,
        currentRevision,
        publishedRevision,
        submittedBy,
        version,
        createdAt,
        updatedAt,
        createdBy,
        updatedBy,
        current);
  }

  public void ensureVersion(long expectedVersion) {
    if (this.version != expectedVersion) {
      throw new OptimisticConcurrencyException();
    }
  }

  public void updateDraft(
      DemonstrationRevisionContent content,
      Map<UUID, DemonstrationSource> sources,
      Instant now,
      String actor) {
    requireDraft();
    if (current.frozen()) {
      throw new InvalidStateTransitionException();
    }
    String subject = requireSubject(actor);
    current =
        content.toRevision(
            current.id(), current.revisionNumber(), false, current.createdAt(), current.createdBy(), sources);
    touch(now, subject);
  }

  public void submit(AdministrativeJustification justification, Instant now, String actor) {
    requireDraft();
    String subject = requireSubject(actor);
    current = freezeCurrent();
    workflowStatus = DemonstrationWorkflowStatus.UNDER_REVIEW;
    submittedBy = subject;
    pendingDecisions.add(
        new DemonstrationDecision(
            UUID.randomUUID(),
            current.revisionNumber(),
            "SUBMITTED",
            subject,
            justification.value(),
            now));
    touch(now, subject);
  }

  public void returnForChanges(
      DemonstrationRevisionContent content,
      Map<UUID, DemonstrationSource> sources,
      AdministrativeJustification justification,
      Instant now,
      String actor) {
    if (workflowStatus != DemonstrationWorkflowStatus.UNDER_REVIEW) {
      throw new InvalidStateTransitionException();
    }
    String subject = requireSubject(actor);
    pendingDecisions.add(
        new DemonstrationDecision(
            UUID.randomUUID(),
            current.revisionNumber(),
            "RETURNED",
            subject,
            justification.value(),
            now));
    int next = currentRevision + 1;
    current = content.toRevision(UUID.randomUUID(), next, false, now, subject, sources);
    currentRevision = next;
    workflowStatus = DemonstrationWorkflowStatus.DRAFT;
    submittedBy = null;
    touch(now, subject);
  }

  public void approve(AdministrativeJustification justification, Instant now, String actor) {
    if (workflowStatus != DemonstrationWorkflowStatus.UNDER_REVIEW) {
      throw new InvalidStateTransitionException();
    }
    String subject = requireSubject(actor);
    if (subject.equals(submittedBy)) {
      throw new SegregationOfDutiesException();
    }
    workflowStatus = DemonstrationWorkflowStatus.APPROVED;
    pendingDecisions.add(
        new DemonstrationDecision(
            UUID.randomUUID(),
            current.revisionNumber(),
            "APPROVED",
            subject,
            justification.value(),
            now));
    touch(now, subject);
  }

  public void publish(AdministrativeJustification justification, Instant now, String actor) {
    if (workflowStatus != DemonstrationWorkflowStatus.APPROVED) {
      throw new InvalidStateTransitionException();
    }
    if (publicationStatus == DemonstrationPublicationStatus.RETIRED) {
      throw new InvalidStateTransitionException();
    }
    String subject = requireSubject(actor);
    publicationStatus = DemonstrationPublicationStatus.LIVE;
    publishedRevision = currentRevision;
    pendingDecisions.add(
        new DemonstrationDecision(
            UUID.randomUUID(),
            current.revisionNumber(),
            "PUBLISHED",
            subject,
            justification.value(),
            now));
    touch(now, subject);
  }

  public void pause(AdministrativeJustification justification, Instant now, String actor) {
    if (publicationStatus != DemonstrationPublicationStatus.LIVE) {
      throw new InvalidStateTransitionException();
    }
    String subject = requireSubject(actor);
    publicationStatus = DemonstrationPublicationStatus.PAUSED;
    pendingDecisions.add(
        new DemonstrationDecision(
            UUID.randomUUID(),
            publishedRevision == null ? currentRevision : publishedRevision,
            "PAUSED",
            subject,
            justification.value(),
            now));
    touch(now, subject);
  }

  public void resume(AdministrativeJustification justification, Instant now, String actor) {
    if (publicationStatus != DemonstrationPublicationStatus.PAUSED) {
      throw new InvalidStateTransitionException();
    }
    String subject = requireSubject(actor);
    publicationStatus = DemonstrationPublicationStatus.LIVE;
    pendingDecisions.add(
        new DemonstrationDecision(
            UUID.randomUUID(),
            publishedRevision,
            "RESUMED",
            subject,
            justification.value(),
            now));
    touch(now, subject);
  }

  public void retire(AdministrativeJustification justification, Instant now, String actor) {
    if (publicationStatus != DemonstrationPublicationStatus.LIVE
        && publicationStatus != DemonstrationPublicationStatus.PAUSED) {
      throw new InvalidStateTransitionException();
    }
    String subject = requireSubject(actor);
    publicationStatus = DemonstrationPublicationStatus.RETIRED;
    pendingDecisions.add(
        new DemonstrationDecision(
            UUID.randomUUID(),
            publishedRevision,
            "RETIRED",
            subject,
            justification.value(),
            now));
    touch(now, subject);
  }

  public void newDraft(
      DemonstrationRevisionContent content,
      Map<UUID, DemonstrationSource> sources,
      Instant now,
      String actor) {
    if (workflowStatus != DemonstrationWorkflowStatus.APPROVED
        && publicationStatus != DemonstrationPublicationStatus.LIVE
        && publicationStatus != DemonstrationPublicationStatus.PAUSED) {
      throw new InvalidStateTransitionException();
    }
    if (publicationStatus == DemonstrationPublicationStatus.RETIRED) {
      throw new InvalidStateTransitionException();
    }
    String subject = requireSubject(actor);
    int next = currentRevision + 1;
    current = content.toRevision(UUID.randomUUID(), next, false, now, subject, sources);
    currentRevision = next;
    workflowStatus = DemonstrationWorkflowStatus.DRAFT;
    submittedBy = null;
    touch(now, subject);
  }

  public boolean publiclyVisible() {
    return publicationStatus == DemonstrationPublicationStatus.LIVE && publishedRevision != null;
  }

  public UUID id() {
    return id;
  }

  public ResourceKey key() {
    return key;
  }

  public DemonstrationWorkflowStatus workflowStatus() {
    return workflowStatus;
  }

  public DemonstrationPublicationStatus publicationStatus() {
    return publicationStatus;
  }

  public int currentRevision() {
    return currentRevision;
  }

  public Integer publishedRevision() {
    return publishedRevision;
  }

  public String submittedBy() {
    return submittedBy;
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

  public DemonstrationRevision current() {
    return current;
  }

  public List<DemonstrationDecision> pendingDecisions() {
    return List.copyOf(pendingDecisions);
  }

  public void clearPendingDecisions() {
    pendingDecisions.clear();
  }

  private void requireDraft() {
    if (workflowStatus != DemonstrationWorkflowStatus.DRAFT) {
      throw new InvalidStateTransitionException();
    }
  }

  private DemonstrationRevision freezeCurrent() {
    return new DemonstrationRevision(
        current.id(),
        current.revisionNumber(),
        current.title(),
        current.summary(),
        current.intendedAudience(),
        current.scopeNote(),
        true,
        current.createdAt(),
        current.createdBy(),
        current.blocks(),
        current.claims());
  }

  private void touch(Instant now, String actor) {
    this.updatedAt = Objects.requireNonNull(now);
    this.updatedBy = actor;
  }

  private static String requireSubject(String actor) {
    if (actor == null || actor.isBlank()) {
      throw new CatalogValidationException("O ator administrativo é obrigatório.");
    }
    return actor.trim();
  }

  public record DemonstrationRevisionContent(
      String title,
      String summary,
      String intendedAudience,
      String scopeNote,
      List<DemonstrationBlock> blocks,
      List<DemonstrationClaim> claims) {

    public DemonstrationRevisionContent {
      title = DemonstrationText.required(title, "O título", 3, 200);
      summary = DemonstrationText.required(summary, "O resumo", 10, 1000);
      intendedAudience = DemonstrationText.required(intendedAudience, "O público pretendido", 3, 200);
      scopeNote = DemonstrationText.required(scopeNote, "A nota de escopo", 10, 1000);
      blocks = blocks == null ? List.of() : List.copyOf(blocks);
      claims = claims == null ? List.of() : List.copyOf(claims);
    }

    public DemonstrationRevision toRevision(
        UUID id,
        int revisionNumber,
        boolean frozen,
        Instant createdAt,
        String createdBy,
        Map<UUID, DemonstrationSource> sources) {
      if (blocks == null || blocks.isEmpty()) {
        throw new CatalogValidationException("A demonstração precisa de ao menos um bloco narrativo.");
      }
      HashSet<Integer> blockPositions = new HashSet<>();
      for (DemonstrationBlock block : blocks) {
        if (!blockPositions.add(block.position())) {
          throw new CatalogValidationException("Os blocos não podem repetir posição.");
        }
      }
      List<DemonstrationClaim> safeClaims = claims == null ? List.of() : claims;
      HashSet<Integer> claimPositions = new HashSet<>();
      for (DemonstrationClaim claim : safeClaims) {
        if (!claimPositions.add(claim.position())) {
          throw new CatalogValidationException("As alegações não podem repetir posição.");
        }
        DemonstrationSource source = sources.get(claim.sourceId());
        if (source == null || !source.usableForClaim()) {
          throw new CatalogValidationException(
              "Cada alegação factual precisa de uma fonte pública verificada.");
        }
      }
      Map<Integer, DemonstrationBlock> byPosition =
          blocks.stream().collect(Collectors.toMap(DemonstrationBlock::position, Function.identity()));
      List<DemonstrationBlock> ordered = new ArrayList<>();
      for (int i = 1; i <= blocks.size(); i++) {
        DemonstrationBlock block = byPosition.get(i);
        if (block == null) {
          throw new CatalogValidationException("Os blocos devem ser contínuos a partir de 1.");
        }
        ordered.add(block);
      }
      return new DemonstrationRevision(
          id,
          revisionNumber,
          title,
          summary,
          intendedAudience,
          scopeNote,
          frozen,
          createdAt,
          createdBy,
          ordered,
          safeClaims);
    }
  }
}
