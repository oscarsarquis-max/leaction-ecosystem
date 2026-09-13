package br.com.segsense.application.demonstration;

import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.demonstration.DemonstrationRevision;
import br.com.segsense.domain.demonstration.DemonstrationStory;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DemonstrationStoryRepository {

  DemonstrationStory save(DemonstrationStory story);

  Optional<DemonstrationStory> findById(UUID id);

  Optional<DemonstrationStory> findByKey(ResourceKey key);

  boolean existsByKey(ResourceKey key);

  List<DemonstrationStory> listAll();

  Optional<DemonstrationStory> findPublishedByKey(ResourceKey key);

  Optional<DemonstrationRevision> findRevision(UUID storyId, int revisionNumber);

  Optional<Instant> lastPublicationAt(UUID storyId);
}
