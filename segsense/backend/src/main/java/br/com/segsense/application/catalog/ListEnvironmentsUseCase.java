package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ListEnvironmentsUseCase {

  private final ChannelRepository channels;
  private final EnvironmentRepository environments;

  public ListEnvironmentsUseCase(ChannelRepository channels, EnvironmentRepository environments) {
    this.channels = channels;
    this.environments = environments;
  }

  @Transactional(readOnly = true)
  public CatalogPage<ContextualEnvironment> execute(
      UUID publisherId, UUID channelId, CatalogPageQuery query) {
    channels
        .findByIdAndPublisherId(channelId, publisherId)
        .orElseThrow(ResourceNotFoundException::new);
    CatalogCursor cursor = query.decodedCursor();
    List<ContextualEnvironment> fetched =
        environments.listAfter(publisherId, channelId, cursor, query.size() + 1);
    return CatalogPages.slice(
        fetched, query.size(), ContextualEnvironment::createdAt, ContextualEnvironment::id);
  }
}
