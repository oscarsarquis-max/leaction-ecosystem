package br.com.segsense.application.opportunity;

import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GetOpportunityUseCase {

  private final OpportunityRepository opportunities;

  public GetOpportunityUseCase(OpportunityRepository opportunities) {
    this.opportunities = opportunities;
  }

  @Transactional(readOnly = true)
  public ContextualOpportunity execute(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId) {
    return opportunities
        .findByScope(publisherId, channelId, environmentId, opportunityId)
        .orElseThrow(ResourceNotFoundException::new);
  }
}
