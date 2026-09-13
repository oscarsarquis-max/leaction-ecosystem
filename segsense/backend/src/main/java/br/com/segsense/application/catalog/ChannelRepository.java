package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ResourceKey;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ChannelRepository {

  Channel save(Channel channel);

  Optional<Channel> findByIdAndPublisherId(UUID channelId, UUID publisherId);

  boolean existsByPublisherIdAndKey(UUID publisherId, ResourceKey key);

  List<Channel> listAfter(UUID publisherId, CatalogCursor after, int limit);
}
