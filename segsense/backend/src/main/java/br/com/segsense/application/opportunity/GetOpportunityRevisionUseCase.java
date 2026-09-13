package br.com.segsense.application.opportunity;

import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.opportunity.OpportunityRevision;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GetOpportunityRevisionUseCase {

  private final OpportunityRepository opportunities;

  public GetOpportunityRevisionUseCase(OpportunityRepository opportunities) {
    this.opportunities = opportunities;
  }

  @Transactional(readOnly = true)
  public OpportunityRevision execute(
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      int revisionNumber) {
    opportunities
        .findByScope(publisherId, channelId, environmentId, opportunityId)
        .orElseThrow(ResourceNotFoundException::new);
    return opportunities
        .findRevision(opportunityId, revisionNumber)
        .orElseThrow(ResourceNotFoundException::new);
  }
}
