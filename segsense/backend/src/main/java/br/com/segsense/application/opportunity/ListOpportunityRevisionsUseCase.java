package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogPage;
import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.OpportunityRevision;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ListOpportunityRevisionsUseCase {

  private final OpportunityRepository opportunities;

  public ListOpportunityRevisionsUseCase(OpportunityRepository opportunities) {
    this.opportunities = opportunities;
  }

  @Transactional(readOnly = true)
  public CatalogPage<OpportunityRevision> execute(
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      CatalogPageQuery query) {
    ContextualOpportunity opportunity =
        opportunities
            .findByScope(publisherId, channelId, environmentId, opportunityId)
            .orElseThrow(ResourceNotFoundException::new);
    Integer after =
        query.after() == null
            ? null
            : RevisionHistoryCursor.decode(query.after(), opportunity.id()).revisionNumber();
    List<OpportunityRevision> fetched =
        opportunities.listRevisionsAfter(opportunity.id(), after, query.size() + 1);
    boolean hasNext = fetched.size() > query.size();
    List<OpportunityRevision> items =
        new ArrayList<>(hasNext ? fetched.subList(0, query.size()) : fetched);
    String next = null;
    if (hasNext && !items.isEmpty()) {
      OpportunityRevision last = items.get(items.size() - 1);
      next = RevisionHistoryCursor.encode(opportunity.id(), last.revisionNumber());
    }
    return new CatalogPage<>(items, next, query.size());
  }
}
