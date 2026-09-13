package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogPage;
import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.domain.opportunity.LifecycleEvent;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ListOpportunityLifecycleEventsUseCase {

  private final OpportunityCommandSupport support;
  private final OpportunityRepository opportunities;

  public ListOpportunityLifecycleEventsUseCase(
      OpportunityCommandSupport support, OpportunityRepository opportunities) {
    this.support = support;
    this.opportunities = opportunities;
  }

  @Transactional(readOnly = true)
  public CatalogPage<LifecycleEvent> execute(
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      CatalogPageQuery query) {
    OpportunityCommandSupport.LoadedOpportunity loaded =
        support.load(publisherId, channelId, environmentId, opportunityId);
    boolean hasCursor = query.after() != null;
    LifecycleEventCursor cursor =
        hasCursor ? LifecycleEventCursor.decode(query.after(), loaded.opportunity().id()) : null;
    List<LifecycleEvent> fetched =
        opportunities.listEventsAfter(
            loaded.opportunity().id(),
            hasCursor ? cursor.occurredAt() : null,
            hasCursor ? cursor.id() : null,
            hasCursor,
            query.size() + 1);
    boolean hasNext = fetched.size() > query.size();
    List<LifecycleEvent> items =
        new ArrayList<>(hasNext ? fetched.subList(0, query.size()) : fetched);
    String next = null;
    if (hasNext && !items.isEmpty()) {
      LifecycleEvent last = items.get(items.size() - 1);
      next = LifecycleEventCursor.encode(last.opportunityId(), last.occurredAt(), last.id());
    }
    return new CatalogPage<>(items, next, query.size());
  }
}
