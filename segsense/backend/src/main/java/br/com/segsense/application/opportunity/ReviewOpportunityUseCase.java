package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogActor;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.DecisionOutcome;
import br.com.segsense.domain.opportunity.GovernanceEffect;
import java.time.Clock;
import java.time.Instant;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ReviewOpportunityUseCase {

  private final OpportunityRepository opportunities;
  private final OpportunityCommandSupport support;
  private final Clock clock;

  public ReviewOpportunityUseCase(
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
      long expectedVersion,
      int revisionNumber,
      DecisionOutcome outcome,
      String justification) {
    OpportunityCommandSupport.LoadedOpportunity loaded =
        support.load(publisherId, channelId, environmentId, opportunityId);
    Instant now = Instant.now(clock);
    String subject = support.requireActor(actor).subjectId();
    UUID correlationId = support.requireCorrelation();
    ContextualOpportunity opportunity = loaded.opportunity();
    GovernanceEffect effect =
        switch (outcome) {
          case RETURNED ->
              opportunity.returnForChanges(
                  expectedVersion, revisionNumber, justification, now, subject, correlationId);
          case APPROVED ->
              opportunity.approve(expectedVersion, revisionNumber, now, subject, correlationId);
          case REJECTED ->
              opportunity.reject(
                  expectedVersion, revisionNumber, justification, now, subject, correlationId);
        };
    return opportunities.saveGovernance(opportunity, effect);
  }
}
