package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RenamePublisherUseCase {

  private final PublisherRepository publishers;
  private final Clock clock;

  public RenamePublisherUseCase(PublisherRepository publishers, Clock clock) {
    this.publishers = publishers;
    this.clock = clock;
  }

  @Transactional
  public Publisher execute(CatalogActor actor, UUID publisherId, String name, long expectedVersion) {
    Objects.requireNonNull(actor, "actor");
    Publisher publisher =
        publishers.findById(publisherId).orElseThrow(ResourceNotFoundException::new);
    publisher.requireExpectedVersion(expectedVersion);
    publisher.rename(DisplayName.parse(name), Instant.now(clock), actor.subjectId());
    return publishers.save(publisher);
  }
}
