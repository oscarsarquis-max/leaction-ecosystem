package br.com.segsense.application.link;

import br.com.segsense.application.catalog.CatalogActor;
import br.com.segsense.application.opportunity.OpportunityCommandSupport;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.link.PublishedContextLink;
import java.time.Clock;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RevokeContextLinkUseCase {

  private final OpportunityCommandSupport support;
  private final PublishedContextLinkRepository links;
  private final Clock clock;

  public RevokeContextLinkUseCase(
      OpportunityCommandSupport support, PublishedContextLinkRepository links, Clock clock) {
    this.support = support;
    this.links = links;
    this.clock = clock;
  }

  @Transactional
  public PublishedContextLink execute(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      UUID linkId,
      long expectedVersion,
      String justification) {
    CatalogActor required = support.requireActor(actor);
    UUID correlationId = support.requireCorrelation();
    support.load(publisherId, channelId, environmentId, opportunityId);
    PublishedContextLink link =
        links
            .findByScope(publisherId, channelId, environmentId, opportunityId, linkId)
            .orElseThrow(ResourceNotFoundException::new);
    var event =
        link.revoke(
            expectedVersion, justification, clock.instant(), required.subjectId(), correlationId);
    return links.saveRevocation(link, event);
  }
}
