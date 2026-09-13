package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ContextualEnvironment;
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
public class TransitionEnvironmentStatusUseCase {

  private final PublisherRepository publishers;
  private final ChannelRepository channels;
  private final EnvironmentRepository environments;
  private final Clock clock;

  public TransitionEnvironmentStatusUseCase(
      PublisherRepository publishers,
      ChannelRepository channels,
      EnvironmentRepository environments,
      Clock clock) {
    this.publishers = publishers;
    this.channels = channels;
    this.environments = environments;
    this.clock = clock;
  }

  @Transactional
  public ContextualEnvironment execute(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
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
    ContextualEnvironment environment =
        environments
            .findByIdAndPublisherIdAndChannelId(environmentId, publisherId, channelId)
            .orElseThrow(ResourceNotFoundException::new);
    environment.requireExpectedVersion(expectedVersion);
    environment.transitionTo(target, publisher, channel, Instant.now(clock), actor.subjectId());
    return environments.save(environment);
  }
}
