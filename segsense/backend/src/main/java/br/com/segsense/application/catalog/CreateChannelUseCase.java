package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ChannelType;
import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
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
public class CreateChannelUseCase {

  private final PublisherRepository publishers;
  private final ChannelRepository channels;
  private final Clock clock;

  public CreateChannelUseCase(
      PublisherRepository publishers, ChannelRepository channels, Clock clock) {
    this.publishers = publishers;
    this.channels = channels;
    this.clock = clock;
  }

  @Transactional
  public Channel execute(
      CatalogActor actor, UUID publisherId, String key, String name, ChannelType type) {
    Objects.requireNonNull(actor, "actor");
    Objects.requireNonNull(type, "type");
    Publisher publisher =
        publishers.findById(publisherId).orElseThrow(ResourceNotFoundException::new);
    ResourceKey resourceKey = ResourceKey.parse(key);
    DisplayName displayName = DisplayName.parse(name);
    if (channels.existsByPublisherIdAndKey(publisher.id(), resourceKey)) {
      throw new DuplicateResourceKeyException(
          "CHANNEL_KEY_CONFLICT", "Já existe um canal com esta chave neste publicador.");
    }
    Channel channel =
        Channel.create(
            UUID.randomUUID(),
            publisher,
            resourceKey,
            displayName,
            type,
            Instant.now(clock),
            actor.subjectId());
    return channels.save(channel);
  }
}
