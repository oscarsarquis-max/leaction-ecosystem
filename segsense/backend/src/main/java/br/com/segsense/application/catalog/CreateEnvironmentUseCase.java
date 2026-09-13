package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.CanonicalUrl;
import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.EnvironmentType;
import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CreateEnvironmentUseCase {

  private final PublisherRepository publishers;
  private final ChannelRepository channels;
  private final EnvironmentRepository environments;
  private final Clock clock;

  public CreateEnvironmentUseCase(
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
      String key,
      String name,
      EnvironmentType type,
      String canonicalUrl) {
    Objects.requireNonNull(actor, "actor");
    Objects.requireNonNull(type, "type");
    Publisher publisher =
        publishers.findById(publisherId).orElseThrow(ResourceNotFoundException::new);
    Channel channel =
        channels
            .findByIdAndPublisherId(channelId, publisherId)
            .orElseThrow(ResourceNotFoundException::new);
    ResourceKey resourceKey = ResourceKey.parse(key);
    DisplayName displayName = DisplayName.parse(name);
    CanonicalUrl url = CanonicalUrl.parseOptional(canonicalUrl).orElse(null);
    if (environments.existsByChannelIdAndKey(channel.id(), resourceKey)) {
      throw new DuplicateResourceKeyException(
          "ENVIRONMENT_KEY_CONFLICT", "Já existe um ambiente com esta chave neste canal.");
    }
    ContextualEnvironment environment =
        ContextualEnvironment.create(
            UUID.randomUUID(),
            publisher,
            channel,
            resourceKey,
            displayName,
            type,
            url,
            Instant.now(clock),
            actor.subjectId());
    return environments.save(environment);
  }
}
