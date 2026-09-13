package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.LifecycleStatus;
import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TransitionChannelStatusUseCase {

  private final PublisherRepository publishers;
  private final ChannelRepository channels;
  private final Clock clock;

  public TransitionChannelStatusUseCase(
      PublisherRepository publishers, ChannelRepository channels, Clock clock) {
    this.publishers = publishers;
    this.channels = channels;
    this.clock = clock;
  }

  @Transactional
  public Channel execute(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      LifecycleStatus target,
      long expectedVersion) {
    Objects.requireNonNull(actor, "actor");
    Objects.requireNonNull(target, "target");
    Publisher publisher =
        publishers.findById(publisherId).orElseThrow(ResourceNotFoundException::new);
    Channel channel =
        channels
            .findByIdAndPublisherId(channelId, publisherId)
            .orElseThrow(ResourceNotFoundException::new);
    channel.requireExpectedVersion(expectedVersion);
    channel.transitionTo(target, publisher, Instant.now(clock), actor.subjectId());
    return channels.save(channel);
  }
}
