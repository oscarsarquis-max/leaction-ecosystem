package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogCursor;
import br.com.segsense.application.catalog.CatalogPage;
import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.application.catalog.CatalogPages;
import br.com.segsense.application.catalog.EnvironmentRepository;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ListOpportunitiesUseCase {

  private final EnvironmentRepository environments;
  private final OpportunityRepository opportunities;

  public ListOpportunitiesUseCase(
      EnvironmentRepository environments, OpportunityRepository opportunities) {
    this.environments = environments;
    this.opportunities = opportunities;
  }

  @Transactional(readOnly = true)
  public CatalogPage<ContextualOpportunity> execute(
      UUID publisherId, UUID channelId, UUID environmentId, CatalogPageQuery query) {
    environments
        .findByIdAndPublisherIdAndChannelId(environmentId, publisherId, channelId)
        .orElseThrow(ResourceNotFoundException::new);
    CatalogCursor cursor = query.decodedCursor();
    List<ContextualOpportunity> fetched =
        opportunities.listAfter(publisherId, channelId, environmentId, cursor, query.size() + 1);
    return CatalogPages.slice(
        fetched, query.size(), ContextualOpportunity::createdAt, ContextualOpportunity::id);
  }
}
