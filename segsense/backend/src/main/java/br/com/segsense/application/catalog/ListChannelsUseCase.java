package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ListChannelsUseCase {

  private final PublisherRepository publishers;
  private final ChannelRepository channels;

  public ListChannelsUseCase(PublisherRepository publishers, ChannelRepository channels) {
    this.publishers = publishers;
    this.channels = channels;
  }

  @Transactional(readOnly = true)
  public CatalogPage<Channel> execute(UUID publisherId, CatalogPageQuery query) {
    publishers.findById(publisherId).orElseThrow(ResourceNotFoundException::new);
    CatalogCursor cursor = query.decodedCursor();
    List<Channel> fetched = channels.listAfter(publisherId, cursor, query.size() + 1);
    return CatalogPages.slice(fetched, query.size(), Channel::createdAt, Channel::id);
  }
}
