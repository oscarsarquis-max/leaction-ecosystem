package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.ResourceKey;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface EnvironmentRepository {

  ContextualEnvironment save(ContextualEnvironment environment);

  Optional<ContextualEnvironment> findByIdAndPublisherIdAndChannelId(
      UUID environmentId, UUID publisherId, UUID channelId);

  boolean existsByChannelIdAndKey(UUID channelId, ResourceKey key);

  List<ContextualEnvironment> listAfter(
      UUID publisherId, UUID channelId, CatalogCursor after, int limit);
}
