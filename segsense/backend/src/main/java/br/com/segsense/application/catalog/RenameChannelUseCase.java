package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RenameChannelUseCase {

  private final ChannelRepository channels;
  private final Clock clock;

  public RenameChannelUseCase(ChannelRepository channels, Clock clock) {
    this.channels = channels;
    this.clock = clock;
  }

  @Transactional
  public Channel execute(
      CatalogActor actor, UUID publisherId, UUID channelId, String name, long expectedVersion) {
    Objects.requireNonNull(actor, "actor");
    Channel channel =
        channels
            .findByIdAndPublisherId(channelId, publisherId)
            .orElseThrow(ResourceNotFoundException::new);
    channel.requireExpectedVersion(expectedVersion);
    channel.rename(DisplayName.parse(name), Instant.now(clock), actor.subjectId());
    return channels.save(channel);
  }
}
