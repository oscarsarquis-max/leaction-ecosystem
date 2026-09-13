package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogCursor;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.GovernanceEffect;
import br.com.segsense.domain.opportunity.LifecycleEvent;
import br.com.segsense.domain.opportunity.OpportunityDecision;
import br.com.segsense.domain.opportunity.OpportunityRevision;
import br.com.segsense.domain.opportunity.OpportunitySubmission;
import br.com.segsense.domain.catalog.ResourceKey;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface OpportunityRepository {

  ContextualOpportunity saveNew(ContextualOpportunity opportunity);

  ContextualOpportunity saveNewRevision(ContextualOpportunity opportunity);

  ContextualOpportunity saveGovernance(ContextualOpportunity opportunity, GovernanceEffect effect);

  Optional<ContextualOpportunity> findByScope(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId);

  boolean existsByEnvironmentIdAndKey(UUID environmentId, ResourceKey key);

  List<ContextualOpportunity> listAfter(
      UUID publisherId, UUID channelId, UUID environmentId, CatalogCursor after, int limit);

  List<OpportunityRevision> listRevisionsAfter(
      UUID opportunityId, Integer afterRevisionNumber, int limit);

  Optional<OpportunityRevision> findRevision(UUID opportunityId, int revisionNumber);

  Optional<OpportunitySubmission> findOpenSubmission(UUID opportunityId);

  Optional<OpportunityDecision> findLatestDecision(UUID opportunityId);

  List<LifecycleEvent> listEventsAfter(
      UUID opportunityId, Instant occurredAt, UUID afterId, boolean hasCursor, int limit);
}
