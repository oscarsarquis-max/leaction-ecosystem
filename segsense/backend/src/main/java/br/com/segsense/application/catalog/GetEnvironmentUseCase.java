package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GetEnvironmentUseCase {

  private final EnvironmentRepository environments;

  public GetEnvironmentUseCase(EnvironmentRepository environments) {
    this.environments = environments;
  }

  @Transactional(readOnly = true)
  public ContextualEnvironment execute(UUID publisherId, UUID channelId, UUID environmentId) {
    return environments
        .findByIdAndPublisherIdAndChannelId(environmentId, publisherId, channelId)
        .orElseThrow(ResourceNotFoundException::new);
  }
}
