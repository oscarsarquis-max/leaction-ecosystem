package br.com.segsense.infrastructure.demonstration;

import br.com.segsense.application.demonstration.DemonstrationStoryRepository;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.demonstration.DemonstrationBlock;
import br.com.segsense.domain.demonstration.DemonstrationClaim;
import br.com.segsense.domain.demonstration.DemonstrationPublicationStatus;
import br.com.segsense.domain.demonstration.DemonstrationRevision;
import br.com.segsense.domain.demonstration.DemonstrationStory;
import br.com.segsense.domain.demonstration.DemonstrationWorkflowStatus;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Repository;

@Repository
public class JpaDemonstrationStoryRepository implements DemonstrationStoryRepository {

  private final DemonstrationStorySpringRepository stories;
  private final DemonstrationRevisionSpringRepository revisions;
  private final DemonstrationBlockSpringRepository blocks;
  private final DemonstrationClaimSpringRepository claims;
  private final DemonstrationDecisionSpringRepository decisions;

  public JpaDemonstrationStoryRepository(
      DemonstrationStorySpringRepository stories,
      DemonstrationRevisionSpringRepository revisions,
      DemonstrationBlockSpringRepository blocks,
      DemonstrationClaimSpringRepository claims,
      DemonstrationDecisionSpringRepository decisions) {
    this.stories = stories;
    this.revisions = revisions;
    this.blocks = blocks;
    this.claims = claims;
    this.decisions = decisions;
  }

  @Override
  public DemonstrationStory save(DemonstrationStory story) {
    DemonstrationStoryJpaEntity entity =
        stories.findById(story.id()).orElseGet(DemonstrationStoryJpaEntity::new);
    boolean creating = entity.getId() == null;
    entity.setId(story.id());
    entity.setStoryKey(story.key().value());
    entity.setWorkflowStatus(story.workflowStatus().name());
    entity.setPublicationStatus(story.publicationStatus().name());
    entity.setCurrentRevision(story.currentRevision());
    entity.setPublishedRevision(story.publishedRevision());
    entity.setSubmittedBy(story.submittedBy());
    entity.setUpdatedAt(story.updatedAt());
    entity.setUpdatedBy(story.updatedBy());
    if (creating) {
      entity.setCreatedAt(story.createdAt());
      entity.setCreatedBy(story.createdBy());
    }
    try {
      stories.saveAndFlush(entity);
      persistRevision(story);
      for (var decision : story.pendingDecisions()) {
        DemonstrationDecisionJpaEntity row = new DemonstrationDecisionJpaEntity();
        row.setId(decision.id());
        row.setStoryId(story.id());
        row.setRevisionNumber(decision.revisionNumber());
        row.setAction(decision.action());
        row.setActor(decision.actor());
        row.setJustification(decision.justification());
        row.setDecidedAt(decision.decidedAt());
        decisions.save(row);
      }
      story.clearPendingDecisions();
      stories.flush();
      return findById(story.id()).orElseThrow();
    } catch (DataIntegrityViolationException ex) {
      throw new DuplicateResourceKeyException(
          "DEMONSTRATION_KEY_CONFLICT", "Já existe uma demonstração com esta chave.");
    }
  }

  private void persistRevision(DemonstrationStory story) {
    DemonstrationRevision current = story.current();
    Optional<DemonstrationRevisionJpaEntity> existing =
        revisions.findByStoryIdAndRevisionNumber(story.id(), current.revisionNumber());
    DemonstrationRevisionJpaEntity row = existing.orElseGet(DemonstrationRevisionJpaEntity::new);
    boolean creating = row.getId() == null;
    row.setId(current.id());
    row.setStoryId(story.id());
    row.setRevisionNumber(current.revisionNumber());
    if (creating || !current.frozen() || (existing.isPresent() && !existing.get().isFrozen())) {
      if (!current.frozen() || creating) {
        row.setTitle(current.title());
        row.setSummary(current.summary());
        row.setIntendedAudience(current.intendedAudience());
        row.setScopeNote(current.scopeNote());
      }
    }
    if (creating) {
      row.setTitle(current.title());
      row.setSummary(current.summary());
      row.setIntendedAudience(current.intendedAudience());
      row.setScopeNote(current.scopeNote());
      row.setCreatedAt(current.createdAt());
      row.setCreatedBy(current.createdBy());
    }
    row.setFrozen(current.frozen());
    revisions.saveAndFlush(row);
    if (!current.frozen() || creating) {
      replaceChildren(story.id(), current);
    }
  }

  private void replaceChildren(UUID storyId, DemonstrationRevision current) {
    claims.deleteByStoryIdAndRevisionNumber(storyId, current.revisionNumber());
    blocks.deleteByStoryIdAndRevisionNumber(storyId, current.revisionNumber());
    blocks.flush();
    claims.flush();
    for (DemonstrationBlock block : current.blocks()) {
      DemonstrationBlockJpaEntity row = new DemonstrationBlockJpaEntity();
      row.setId(block.id());
      row.setStoryId(storyId);
      row.setRevisionNumber(current.revisionNumber());
      row.setPosition(block.position());
      row.setTitle(block.title());
      row.setBody(block.body());
      blocks.save(row);
    }
    for (DemonstrationClaim claim : current.claims()) {
      DemonstrationClaimJpaEntity row = new DemonstrationClaimJpaEntity();
      row.setId(claim.id());
      row.setStoryId(storyId);
      row.setRevisionNumber(current.revisionNumber());
      row.setPosition(claim.position());
      row.setClaimText(claim.text());
      row.setSourceId(claim.sourceId());
      claims.save(row);
    }
    blocks.flush();
    claims.flush();
  }

  @Override
  public Optional<DemonstrationStory> findById(UUID id) {
    return stories.findById(id).flatMap(this::hydrateCurrent);
  }

  @Override
  public Optional<DemonstrationStory> findByKey(ResourceKey key) {
    return stories.findByStoryKey(key.value()).flatMap(this::hydrateCurrent);
  }

  @Override
  public boolean existsByKey(ResourceKey key) {
    return stories.existsByStoryKey(key.value());
  }

  @Override
  public List<DemonstrationStory> listAll() {
    return stories.findAllByOrderByCreatedAtAsc().stream()
        .map(this::hydrateCurrent)
        .flatMap(Optional::stream)
        .toList();
  }

  @Override
  public Optional<DemonstrationStory> findPublishedByKey(ResourceKey key) {
    return stories
        .findByStoryKey(key.value())
        .filter(entity -> DemonstrationPublicationStatus.LIVE.name().equals(entity.getPublicationStatus()))
        .flatMap(this::hydrateCurrent);
  }

  @Override
  public Optional<DemonstrationRevision> findRevision(UUID storyId, int revisionNumber) {
    return revisions
        .findByStoryIdAndRevisionNumber(storyId, revisionNumber)
        .map(this::toRevision);
  }

  @Override
  public Optional<Instant> lastPublicationAt(UUID storyId) {
    return decisions.lastPublicationAt(storyId);
  }

  private Optional<DemonstrationStory> hydrateCurrent(DemonstrationStoryJpaEntity entity) {
    return revisions
        .findByStoryIdAndRevisionNumber(entity.getId(), entity.getCurrentRevision())
        .map(revision -> toDomain(entity, toRevision(revision)));
  }

  private DemonstrationRevision toRevision(DemonstrationRevisionJpaEntity entity) {
    List<DemonstrationBlock> blockList =
        blocks
            .findByStoryIdAndRevisionNumberOrderByPositionAsc(
                entity.getStoryId(), entity.getRevisionNumber())
            .stream()
            .map(
                row ->
                    new DemonstrationBlock(
                        row.getId(), row.getPosition(), row.getTitle(), row.getBody()))
            .toList();
    List<DemonstrationClaim> claimList =
        claims
            .findByStoryIdAndRevisionNumberOrderByPositionAsc(
                entity.getStoryId(), entity.getRevisionNumber())
            .stream()
            .map(
                row ->
                    new DemonstrationClaim(
                        row.getId(), row.getPosition(), row.getClaimText(), row.getSourceId()))
            .toList();
    return new DemonstrationRevision(
        entity.getId(),
        entity.getRevisionNumber(),
        entity.getTitle(),
        entity.getSummary(),
        entity.getIntendedAudience(),
        entity.getScopeNote(),
        entity.isFrozen(),
        entity.getCreatedAt(),
        entity.getCreatedBy(),
        blockList,
        claimList);
  }

  private DemonstrationStory toDomain(
      DemonstrationStoryJpaEntity entity, DemonstrationRevision current) {
    return DemonstrationStory.restore(
        entity.getId(),
        ResourceKey.restored(entity.getStoryKey()),
        DemonstrationWorkflowStatus.valueOf(entity.getWorkflowStatus()),
        DemonstrationPublicationStatus.valueOf(entity.getPublicationStatus()),
        entity.getCurrentRevision(),
        entity.getPublishedRevision(),
        entity.getSubmittedBy(),
        entity.getVersion() == null ? 0L : entity.getVersion(),
        entity.getCreatedAt(),
        entity.getUpdatedAt(),
        entity.getCreatedBy(),
        entity.getUpdatedBy(),
        current);
  }
}
