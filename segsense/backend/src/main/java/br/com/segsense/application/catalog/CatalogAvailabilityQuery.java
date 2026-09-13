package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CatalogAvailabilityQuery {

  private final PublisherRepository publishers;
  private final ChannelRepository channels;
  private final EnvironmentRepository environments;

  public CatalogAvailabilityQuery(
      PublisherRepository publishers,
      ChannelRepository channels,
      EnvironmentRepository environments) {
    this.publishers = publishers;
    this.channels = channels;
    this.environments = environments;
  }

  @Transactional(readOnly = true)
  public boolean publisherAvailable(Publisher publisher) {
    return publisher.effectivelyAvailable();
  }

  @Transactional(readOnly = true)
  public boolean channelAvailable(Channel channel) {
    Publisher publisher =
        publishers.findById(channel.publisherId()).orElseThrow(ResourceNotFoundException::new);
    return channel.effectivelyAvailable(publisher);
  }

  @Transactional(readOnly = true)
  public boolean environmentAvailable(ContextualEnvironment environment) {
    Publisher publisher =
        publishers
            .findById(environment.publisherId())
            .orElseThrow(ResourceNotFoundException::new);
    Channel channel =
        channels
            .findByIdAndPublisherId(environment.channelId(), environment.publisherId())
            .orElseThrow(ResourceNotFoundException::new);
    return environment.effectivelyAvailable(publisher, channel);
  }

  @Transactional(readOnly = true)
  public Publisher requirePublisher(UUID publisherId) {
    return publishers.findById(publisherId).orElseThrow(ResourceNotFoundException::new);
  }

  @Transactional(readOnly = true)
  public CatalogHierarchy requireEnvironmentHierarchy(
      UUID publisherId, UUID channelId, UUID environmentId) {
    Publisher publisher = requirePublisher(publisherId);
    Channel channel =
        channels
            .findByIdAndPublisherId(channelId, publisherId)
            .orElseThrow(ResourceNotFoundException::new);
    ContextualEnvironment environment =
        environments
            .findByIdAndPublisherIdAndChannelId(environmentId, publisherId, channelId)
            .orElseThrow(ResourceNotFoundException::new);
    return new CatalogHierarchy(publisher, channel, environment);
  }

  public record CatalogHierarchy(
      Publisher publisher, Channel channel, ContextualEnvironment environment) {}
}
