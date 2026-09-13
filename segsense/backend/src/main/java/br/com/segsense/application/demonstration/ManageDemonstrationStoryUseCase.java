package br.com.segsense.application.demonstration;

import br.com.segsense.application.catalog.CatalogActor;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.demonstration.DemonstrationBlock;
import br.com.segsense.domain.demonstration.DemonstrationClaim;
import br.com.segsense.domain.demonstration.DemonstrationSource;
import br.com.segsense.domain.demonstration.DemonstrationStory;
import br.com.segsense.domain.demonstration.DemonstrationStory.DemonstrationRevisionContent;
import br.com.segsense.domain.opportunity.AdministrativeJustification;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ManageDemonstrationStoryUseCase {

  private final DemonstrationStoryRepository stories;
  private final DemonstrationSourceRepository sources;
  private final Clock clock;

  public ManageDemonstrationStoryUseCase(
      DemonstrationStoryRepository stories, DemonstrationSourceRepository sources, Clock clock) {
    this.stories = stories;
    this.sources = sources;
    this.clock = clock;
  }

  @Transactional
  public DemonstrationStory create(CatalogActor actor, String key, DemonstrationDraftCommand draft) {
    ResourceKey resourceKey = ResourceKey.parse(key);
    if (stories.existsByKey(resourceKey)) {
      throw new DuplicateResourceKeyException(
          "DEMONSTRATION_KEY_CONFLICT", "Já existe uma demonstração com esta chave.");
    }
    Instant now = Instant.now(clock);
    DemonstrationStory story =
        DemonstrationStory.create(
            UUID.randomUUID(), resourceKey, content(draft), sourceMap(), now, actor.subjectId());
    return stories.save(story);
  }

  @Transactional
  public DemonstrationStory updateDraft(
      CatalogActor actor, String key, long expectedVersion, DemonstrationDraftCommand draft) {
    DemonstrationStory story = require(key);
    story.ensureVersion(expectedVersion);
    story.updateDraft(content(draft), sourceMap(), Instant.now(clock), actor.subjectId());
    return stories.save(story);
  }

  @Transactional
  public DemonstrationStory submit(
      CatalogActor actor, String key, long expectedVersion, String justification) {
    DemonstrationStory story = require(key);
    story.ensureVersion(expectedVersion);
    story.submit(AdministrativeJustification.required(justification), Instant.now(clock), actor.subjectId());
    return stories.save(story);
  }

  @Transactional
  public DemonstrationStory returnForChanges(
      CatalogActor actor, String key, long expectedVersion, String justification, DemonstrationDraftCommand draft) {
    DemonstrationStory story = require(key);
    story.ensureVersion(expectedVersion);
    story.returnForChanges(
        content(draft),
        sourceMap(),
        AdministrativeJustification.required(justification),
        Instant.now(clock),
        actor.subjectId());
    return stories.save(story);
  }

  @Transactional
  public DemonstrationStory approve(
      CatalogActor actor, String key, long expectedVersion, String justification) {
    DemonstrationStory story = require(key);
    story.ensureVersion(expectedVersion);
    story.approve(AdministrativeJustification.required(justification), Instant.now(clock), actor.subjectId());
    return stories.save(story);
  }

  @Transactional
  public DemonstrationStory publish(
      CatalogActor actor, String key, long expectedVersion, String justification) {
    DemonstrationStory story = require(key);
    story.ensureVersion(expectedVersion);
    story.publish(AdministrativeJustification.required(justification), Instant.now(clock), actor.subjectId());
    return stories.save(story);
  }

  @Transactional
  public DemonstrationStory pause(
      CatalogActor actor, String key, long expectedVersion, String justification) {
    DemonstrationStory story = require(key);
    story.ensureVersion(expectedVersion);
    story.pause(AdministrativeJustification.required(justification), Instant.now(clock), actor.subjectId());
    return stories.save(story);
  }

  @Transactional
  public DemonstrationStory resume(
      CatalogActor actor, String key, long expectedVersion, String justification) {
    DemonstrationStory story = require(key);
    story.ensureVersion(expectedVersion);
    story.resume(AdministrativeJustification.required(justification), Instant.now(clock), actor.subjectId());
    return stories.save(story);
  }

  @Transactional
  public DemonstrationStory retire(
      CatalogActor actor, String key, long expectedVersion, String justification) {
    DemonstrationStory story = require(key);
    story.ensureVersion(expectedVersion);
    story.retire(AdministrativeJustification.required(justification), Instant.now(clock), actor.subjectId());
    return stories.save(story);
  }

  @Transactional
  public DemonstrationStory newDraft(
      CatalogActor actor, String key, long expectedVersion, DemonstrationDraftCommand draft) {
    DemonstrationStory story = require(key);
    story.ensureVersion(expectedVersion);
    story.newDraft(content(draft), sourceMap(), Instant.now(clock), actor.subjectId());
    return stories.save(story);
  }

  @Transactional(readOnly = true)
  public DemonstrationStory get(String key) {
    return require(key);
  }

  @Transactional(readOnly = true)
  public List<DemonstrationStory> list() {
    return stories.listAll();
  }

  @Transactional(readOnly = true)
  public List<DemonstrationSource> sources() {
    return sources.listAll();
  }

  private DemonstrationStory require(String key) {
    return stories.findByKey(ResourceKey.parse(key)).orElseThrow(ResourceNotFoundException::new);
  }

  private Map<UUID, DemonstrationSource> sourceMap() {
    return sources.listAll().stream()
        .collect(Collectors.toMap(DemonstrationSource::id, Function.identity()));
  }

  private DemonstrationRevisionContent content(DemonstrationDraftCommand draft) {
    Objects.requireNonNull(draft, "draft");
    List<DemonstrationBlock> blocks = new ArrayList<>();
    int position = 1;
    for (BlockCommand block : draft.blocks()) {
      blocks.add(
          new DemonstrationBlock(UUID.randomUUID(), position++, block.title(), block.body()));
    }
    List<DemonstrationClaim> claims = new ArrayList<>();
    int claimPosition = 1;
    Map<String, DemonstrationSource> byKey =
        sources.listAll().stream().collect(Collectors.toMap(DemonstrationSource::key, Function.identity()));
    for (ClaimCommand claim : draft.claims()) {
      DemonstrationSource source = byKey.get(claim.sourceKey());
      UUID sourceId = source == null ? UUID.randomUUID() : source.id();
      claims.add(new DemonstrationClaim(UUID.randomUUID(), claimPosition++, claim.text(), sourceId));
    }
    return new DemonstrationRevisionContent(
        draft.title(),
        draft.summary(),
        draft.intendedAudience(),
        draft.scopeNote(),
        blocks,
        claims);
  }

  public record BlockCommand(String title, String body) {}

  public record ClaimCommand(String text, String sourceKey) {}

  public record DemonstrationDraftCommand(
      String title,
      String summary,
      String intendedAudience,
      String scopeNote,
      List<BlockCommand> blocks,
      List<ClaimCommand> claims) {

    public DemonstrationDraftCommand {
      blocks = blocks == null ? List.of() : List.copyOf(blocks);
      claims = claims == null ? List.of() : List.copyOf(claims);
    }
  }
}
