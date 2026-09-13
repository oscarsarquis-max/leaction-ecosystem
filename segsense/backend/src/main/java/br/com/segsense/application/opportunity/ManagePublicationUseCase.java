package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogActor;
import br.com.segsense.application.catalog.CatalogAvailabilityQuery.CatalogHierarchy;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.GovernanceEffect;
import br.com.segsense.domain.opportunity.LifecycleEventType;
import java.time.Clock;
import java.time.Instant;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ManagePublicationUseCase {

  private final OpportunityRepository opportunities;
  private final OpportunityCommandSupport support;
  private final Clock clock;

  public ManagePublicationUseCase(
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
      LifecycleEventType command,
      String justification) {
    OpportunityCommandSupport.LoadedOpportunity loaded =
        support.load(publisherId, channelId, environmentId, opportunityId);
    Instant now = Instant.now(clock);
    String subject = support.requireActor(actor).subjectId();
    UUID correlationId = support.requireCorrelation();
    ContextualOpportunity opportunity = loaded.opportunity();
    CatalogHierarchy hierarchy = loaded.hierarchy();
    GovernanceEffect effect =
        switch (command) {
          case ACTIVATED ->
              opportunity.activatePublication(
                  expectedVersion,
                  now,
                  subject,
                  correlationId,
                  hierarchy.publisher(),
                  hierarchy.channel(),
                  hierarchy.environment());
          case PAUSED -> opportunity.pause(expectedVersion, now, subject, correlationId);
          case RESUMED ->
              opportunity.resume(
                  expectedVersion,
                  now,
                  subject,
                  correlationId,
                  hierarchy.publisher(),
                  hierarchy.channel(),
                  hierarchy.environment());
          case EXPIRED -> opportunity.expire(expectedVersion, now, subject, correlationId);
          case REVOKED ->
              opportunity.revoke(expectedVersion, justification, now, subject, correlationId);
          default -> throw new IllegalArgumentException("unsupported publication command");
        };
    return opportunities.saveGovernance(opportunity, effect);
  }
}
