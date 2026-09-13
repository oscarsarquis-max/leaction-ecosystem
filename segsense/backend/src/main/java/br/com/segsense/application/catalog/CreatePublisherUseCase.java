package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceKey;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CreatePublisherUseCase {

  private final PublisherRepository publishers;
  private final Clock clock;

  public CreatePublisherUseCase(PublisherRepository publishers, Clock clock) {
    this.publishers = publishers;
    this.clock = clock;
  }

  @Transactional
  public Publisher execute(CatalogActor actor, String key, String name) {
    Objects.requireNonNull(actor, "actor");
    ResourceKey resourceKey = ResourceKey.parse(key);
    DisplayName displayName = DisplayName.parse(name);
    if (publishers.existsByKey(resourceKey)) {
      throw new DuplicateResourceKeyException(
          "PUBLISHER_KEY_CONFLICT", "Já existe um publicador com esta chave.");
    }
    Instant now = Instant.now(clock);
    Publisher publisher =
        Publisher.create(UUID.randomUUID(), resourceKey, displayName, now, actor.subjectId());
    return publishers.save(publisher);
  }
}
