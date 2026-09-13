package br.com.segsense.application.opportunity;

import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.GovernanceAction;
import br.com.segsense.domain.opportunity.OpportunityDecision;
import br.com.segsense.domain.opportunity.OpportunityGovernanceActions;
import br.com.segsense.domain.opportunity.OpportunitySubmission;
import br.com.segsense.domain.opportunity.PublicationWindow;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GetOpportunityGovernanceUseCase {

  private final OpportunityRepository opportunities;
  private final OpportunityCommandSupport support;
  private final Clock clock;

  public GetOpportunityGovernanceUseCase(
      OpportunityRepository opportunities, OpportunityCommandSupport support, Clock clock) {
    this.opportunities = opportunities;
    this.support = support;
    this.clock = clock;
  }

  @Transactional(readOnly = true)
  public OpportunityGovernanceView execute(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId) {
    OpportunityCommandSupport.LoadedOpportunity loaded =
        support.load(publisherId, channelId, environmentId, opportunityId);
    ContextualOpportunity opportunity = loaded.opportunity();
    Instant now = Instant.now(clock);
    boolean available =
        opportunity.effectivelyAvailable(
            loaded.hierarchy().publisher(),
            loaded.hierarchy().channel(),
            loaded.hierarchy().environment());
    boolean publishable =
        opportunity.effectivelyPublishable(
            loaded.hierarchy().publisher(),
            loaded.hierarchy().channel(),
            loaded.hierarchy().environment(),
            now);
    boolean published =
        opportunity.effectivelyPublished(
            loaded.hierarchy().publisher(),
            loaded.hierarchy().channel(),
            loaded.hierarchy().environment(),
            now);
    List<GovernanceAction> actions =
        OpportunityGovernanceActions.available(
            opportunity,
            loaded.hierarchy().publisher(),
            loaded.hierarchy().channel(),
            loaded.hierarchy().environment(),
            now);
    OpportunitySubmission open = opportunities.findOpenSubmission(opportunity.id()).orElse(null);
    OpportunityDecision decision = opportunities.findLatestDecision(opportunity.id()).orElse(null);
    return new OpportunityGovernanceView(
        opportunity,
        open,
        decision,
        available,
        publishable,
        published,
        PublicationWindow.isOpen(opportunity.current().content(), now),
        PublicationWindow.isExpired(opportunity.current().content(), now),
        actions);
  }
}
