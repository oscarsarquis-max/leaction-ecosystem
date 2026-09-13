package br.com.segsense.application.catalog;

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
public class TransitionPublisherStatusUseCase {

  private final PublisherRepository publishers;
  private final Clock clock;

  public TransitionPublisherStatusUseCase(PublisherRepository publishers, Clock clock) {
    this.publishers = publishers;
    this.clock = clock;
  }

  @Transactional
  public Publisher execute(
      CatalogActor actor, UUID publisherId, LifecycleStatus target, long expectedVersion) {
    Objects.requireNonNull(actor, "actor");
    Objects.requireNonNull(target, "target");
    Publisher publisher =
        publishers.findById(publisherId).orElseThrow(ResourceNotFoundException::new);
    publisher.requireExpectedVersion(expectedVersion);
    publisher.transitionTo(target, Instant.now(clock), actor.subjectId());
    return publishers.save(publisher);
  }
}
