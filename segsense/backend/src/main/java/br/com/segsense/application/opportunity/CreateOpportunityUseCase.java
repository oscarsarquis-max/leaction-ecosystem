package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogActor;
import br.com.segsense.application.catalog.ChannelRepository;
import br.com.segsense.application.catalog.EnvironmentRepository;
import br.com.segsense.application.catalog.PublisherRepository;
import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.OpportunityContent;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CreateOpportunityUseCase {

  private final PublisherRepository publishers;
  private final ChannelRepository channels;
  private final EnvironmentRepository environments;
  private final OpportunityRepository opportunities;
  private final Clock clock;

  public CreateOpportunityUseCase(
      PublisherRepository publishers,
      ChannelRepository channels,
      EnvironmentRepository environments,
      OpportunityRepository opportunities,
      Clock clock) {
    this.publishers = publishers;
    this.channels = channels;
    this.environments = environments;
    this.opportunities = opportunities;
    this.clock = clock;
  }

  @Transactional
  public ContextualOpportunity execute(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      String key,
      OpportunityContent content) {
    Objects.requireNonNull(actor, "actor");
    Objects.requireNonNull(content, "content");
    Publisher publisher =
        publishers.findById(publisherId).orElseThrow(ResourceNotFoundException::new);
    Channel channel =
        channels
            .findByIdAndPublisherId(channelId, publisherId)
            .orElseThrow(ResourceNotFoundException::new);
    ContextualEnvironment environment =
        environments
            .findByIdAndPublisherIdAndChannelId(environmentId, publisherId, channelId)
            .orElseThrow(ResourceNotFoundException::new);
    ResourceKey resourceKey = ResourceKey.parse(key);
    if (opportunities.existsByEnvironmentIdAndKey(environment.id(), resourceKey)) {
      throw new DuplicateResourceKeyException(
          "OPPORTUNITY_KEY_CONFLICT", "Já existe uma oportunidade com esta chave neste ambiente.");
    }
    ContextualOpportunity opportunity =
        ContextualOpportunity.create(
            UUID.randomUUID(),
            publisher,
            channel,
            environment,
            resourceKey,
            content,
            Instant.now(clock),
            actor.subjectId());
    return opportunities.saveNew(opportunity);
  }
}
