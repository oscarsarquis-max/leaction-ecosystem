package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogActor;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.GovernanceEffect;
import java.time.Clock;
import java.time.Instant;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SubmitOpportunityUseCase {

  private final OpportunityRepository opportunities;
  private final OpportunityCommandSupport support;
  private final Clock clock;

  public SubmitOpportunityUseCase(
      OpportunityRepository opportunities, OpportunityCommandSupport support, Clock clock) {
    this.opportunities = opportunities;
    this.support = support;
    this.clock = clock;
  }

  @Transactional
  public ContextualOpportunity execute(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      long expectedVersion) {
    OpportunityCommandSupport.LoadedOpportunity loaded =
        support.load(publisherId, channelId, environmentId, opportunityId);
    GovernanceEffect effect =
        loaded
            .opportunity()
            .submit(
                expectedVersion,
                Instant.now(clock),
                support.requireActor(actor).subjectId(),
                support.requireCorrelation());
    return opportunities.saveGovernance(loaded.opportunity(), effect);
  }
}
