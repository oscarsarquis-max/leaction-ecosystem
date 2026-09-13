package br.com.segsense.infrastructure.catalog;

import br.com.segsense.application.catalog.CatalogCursor;
import br.com.segsense.application.catalog.PublisherRepository;
import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.LifecycleStatus;
import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceKey;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;

@Repository
public class JpaPublisherRepository implements PublisherRepository {

  private final PublisherSpringRepository spring;

  public JpaPublisherRepository(PublisherSpringRepository spring) {
    this.spring = spring;
  }

  @Override
  public Publisher save(Publisher publisher) {
    PublisherJpaEntity entity =
        spring.findById(publisher.id()).orElseGet(PublisherJpaEntity::new);
    boolean creating = entity.getId() == null;
    entity.setId(publisher.id());
    entity.setKey(publisher.key().value());
    entity.setName(publisher.name().value());
    entity.setStatus(publisher.status().name());
    entity.setUpdatedAt(publisher.updatedAt());
    entity.setUpdatedBy(publisher.updatedBy());
    if (creating) {
      entity.setCreatedAt(publisher.createdAt());
      entity.setCreatedBy(publisher.createdBy());
    }
    try {
      return toDomain(spring.saveAndFlush(entity));
    } catch (DataIntegrityViolationException ex) {
      throw new DuplicateResourceKeyException(
          "PUBLISHER_KEY_CONFLICT", "Já existe um publicador com esta chave.");
    }
  }

  @Override
  public Optional<Publisher> findById(UUID id) {
    return spring.findById(id).map(JpaPublisherRepository::toDomain);
  }

  @Override
  public boolean existsByKey(ResourceKey key) {
    return spring.existsByKey(key.value());
  }

  @Override
  public List<Publisher> listAfter(CatalogCursor after, int limit) {
    boolean hasCursor = after != null;
    Instant createdAt = hasCursor ? after.createdAt() : Instant.EPOCH;
    UUID id = hasCursor ? after.id() : new UUID(0, 0);
    return spring.listAfter(hasCursor, createdAt, id, PageRequest.of(0, limit)).stream()
        .map(JpaPublisherRepository::toDomain)
        .toList();
  }

  static Publisher toDomain(PublisherJpaEntity entity) {
    return Publisher.restore(
        entity.getId(),
        ResourceKey.restored(entity.getKey()),
        DisplayName.parse(entity.getName()),
        LifecycleStatus.valueOf(entity.getStatus()),
        entity.getVersion() == null ? 0L : entity.getVersion(),
        entity.getCreatedAt(),
        entity.getUpdatedAt(),
        entity.getCreatedBy(),
        entity.getUpdatedBy());
  }
}
