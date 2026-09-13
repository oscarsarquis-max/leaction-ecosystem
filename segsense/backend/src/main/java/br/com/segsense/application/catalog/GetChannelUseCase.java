package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GetChannelUseCase {

  private final ChannelRepository channels;

  public GetChannelUseCase(ChannelRepository channels) {
    this.channels = channels;
  }

  @Transactional(readOnly = true)
  public Channel execute(UUID publisherId, UUID channelId) {
    return channels
        .findByIdAndPublisherId(channelId, publisherId)
        .orElseThrow(ResourceNotFoundException::new);
  }
}
