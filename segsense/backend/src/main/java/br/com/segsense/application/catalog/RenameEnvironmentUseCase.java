package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RenameEnvironmentUseCase {

  private final EnvironmentRepository environments;
  private final Clock clock;

  public RenameEnvironmentUseCase(EnvironmentRepository environments, Clock clock) {
    this.environments = environments;
    this.clock = clock;
  }

  @Transactional
  public ContextualEnvironment execute(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      String name,
      long expectedVersion) {
    Objects.requireNonNull(actor, "actor");
    ContextualEnvironment environment =
        environments
            .findByIdAndPublisherIdAndChannelId(environmentId, publisherId, channelId)
            .orElseThrow(ResourceNotFoundException::new);
    environment.requireExpectedVersion(expectedVersion);
    environment.rename(DisplayName.parse(name), Instant.now(clock), actor.subjectId());
    return environments.save(environment);
  }
}
