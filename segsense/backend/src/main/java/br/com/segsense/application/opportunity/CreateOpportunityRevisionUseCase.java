package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogActor;
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
public class CreateOpportunityRevisionUseCase {

  private final OpportunityRepository opportunities;
  private final Clock clock;

  public CreateOpportunityRevisionUseCase(OpportunityRepository opportunities, Clock clock) {
    this.opportunities = opportunities;
    this.clock = clock;
  }

  @Transactional
  public ContextualOpportunity execute(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      long expectedVersion,
      int baseRevision,
      OpportunityContent content) {
    Objects.requireNonNull(actor, "actor");
    Objects.requireNonNull(content, "content");
    ContextualOpportunity opportunity =
        opportunities
            .findByScope(publisherId, channelId, environmentId, opportunityId)
            .orElseThrow(ResourceNotFoundException::new);
    opportunity.revise(
        expectedVersion, baseRevision, content, Instant.now(clock), actor.subjectId());
    return opportunities.saveNewRevision(opportunity);
  }
}
