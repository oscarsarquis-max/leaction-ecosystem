package br.com.segsense.infrastructure.catalog;

import br.com.segsense.application.catalog.CatalogCursor;
import br.com.segsense.application.catalog.ChannelRepository;
import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ChannelType;
import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.LifecycleStatus;
import br.com.segsense.domain.catalog.ResourceKey;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;

@Repository
public class JpaChannelRepository implements ChannelRepository {

  private final ChannelSpringRepository spring;

  public JpaChannelRepository(ChannelSpringRepository spring) {
    this.spring = spring;
  }

  @Override
  public Channel save(Channel channel) {
    ChannelJpaEntity entity = spring.findById(channel.id()).orElseGet(ChannelJpaEntity::new);
    boolean creating = entity.getId() == null;
    entity.setId(channel.id());
    entity.setPublisherId(channel.publisherId());
    entity.setKey(channel.key().value());
    entity.setName(channel.name().value());
    entity.setType(channel.type().name());
    entity.setStatus(channel.status().name());
    entity.setUpdatedAt(channel.updatedAt());
    entity.setUpdatedBy(channel.updatedBy());
    if (creating) {
      entity.setCreatedAt(channel.createdAt());
      entity.setCreatedBy(channel.createdBy());
    }
    try {
      return toDomain(spring.saveAndFlush(entity));
    } catch (DataIntegrityViolationException ex) {
      throw new DuplicateResourceKeyException(
          "CHANNEL_KEY_CONFLICT", "Já existe um canal com esta chave neste publicador.");
    }
  }

  @Override
  public Optional<Channel> findByIdAndPublisherId(UUID channelId, UUID publisherId) {
    return spring.findByIdAndPublisherId(channelId, publisherId).map(JpaChannelRepository::toDomain);
  }

  @Override
  public boolean existsByPublisherIdAndKey(UUID publisherId, ResourceKey key) {
    return spring.existsByPublisherIdAndKey(publisherId, key.value());
  }

  @Override
  public List<Channel> listAfter(UUID publisherId, CatalogCursor after, int limit) {
    boolean hasCursor = after != null;
    Instant createdAt = hasCursor ? after.createdAt() : Instant.EPOCH;
    UUID id = hasCursor ? after.id() : new UUID(0, 0);
    return spring
        .listAfter(publisherId, hasCursor, createdAt, id, PageRequest.of(0, limit))
        .stream()
        .map(JpaChannelRepository::toDomain)
        .toList();
  }

  static Channel toDomain(ChannelJpaEntity entity) {
    return Channel.restore(
        entity.getId(),
        entity.getPublisherId(),
        ResourceKey.restored(entity.getKey()),
        DisplayName.parse(entity.getName()),
        ChannelType.valueOf(entity.getType()),
        LifecycleStatus.valueOf(entity.getStatus()),
        entity.getVersion() == null ? 0L : entity.getVersion(),
        entity.getCreatedAt(),
        entity.getUpdatedAt(),
        entity.getCreatedBy(),
        entity.getUpdatedBy());
  }
}
