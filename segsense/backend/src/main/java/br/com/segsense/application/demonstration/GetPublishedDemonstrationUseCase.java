package br.com.segsense.application.demonstration;

import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.demonstration.DemonstrationNotPublishedException;
import br.com.segsense.domain.demonstration.DemonstrationRevision;
import br.com.segsense.domain.demonstration.DemonstrationSource;
import br.com.segsense.domain.demonstration.DemonstrationStory;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GetPublishedDemonstrationUseCase {

  private final DemonstrationStoryRepository stories;
  private final DemonstrationSourceRepository sources;

  public GetPublishedDemonstrationUseCase(
      DemonstrationStoryRepository stories, DemonstrationSourceRepository sources) {
    this.stories = stories;
    this.sources = sources;
  }

  @Transactional(readOnly = true)
  public PublishedDemonstration execute(String key) {
    DemonstrationStory story =
        stories
            .findPublishedByKey(ResourceKey.parse(key))
            .orElseThrow(DemonstrationNotPublishedException::new);
    if (!story.publiclyVisible()) {
      throw new DemonstrationNotPublishedException();
    }
    DemonstrationRevision revision =
        stories
            .findRevision(story.id(), story.publishedRevision())
            .orElseThrow(DemonstrationNotPublishedException::new);
    Map<UUID, DemonstrationSource> sourceById =
        sources.listAll().stream()
            .collect(Collectors.toMap(DemonstrationSource::id, Function.identity()));
    List<PublishedReference> references =
        revision.claims().stream()
            .map(claim -> sourceById.get(claim.sourceId()))
            .filter(source -> source != null && source.usableForClaim())
            .map(
                source ->
                    new PublishedReference(
                        source.url(), source.consultedOn().toString(), source.verificationStatus()))
            .distinct()
            .toList();
    return new PublishedDemonstration(
        story.key().value(),
        revision.title(),
        revision.summary(),
        revision.intendedAudience(),
        revision.scopeNote(),
        revision.revisionNumber(),
        stories.lastPublicationAt(story.id()).map(java.time.Instant::toString).orElse(story.updatedAt().toString()),
        revision.blocks().stream()
            .map(block -> new PublishedBlock(block.position(), block.title(), block.body()))
            .toList(),
        references);
  }

  public record PublishedBlock(int position, String title, String body) {}

  public record PublishedReference(String url, String consultedOn, String verificationStatus) {}

  public record PublishedDemonstration(
      String key,
      String title,
      String summary,
      String intendedAudience,
      String scopeNote,
      int revisionNumber,
      String publishedAt,
      List<PublishedBlock> blocks,
      List<PublishedReference> references) {}
}
