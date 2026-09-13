package br.com.segsense.application.opportunity;

import br.com.segsense.application.catalog.CatalogActor;
import br.com.segsense.application.catalog.CatalogAvailabilityQuery;
import br.com.segsense.application.catalog.CatalogAvailabilityQuery.CatalogHierarchy;
import br.com.segsense.application.correlation.CorrelationContext;
import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class OpportunityCommandSupport {

  private final OpportunityRepository opportunities;
  private final CatalogAvailabilityQuery availability;

  public OpportunityCommandSupport(
      OpportunityRepository opportunities, CatalogAvailabilityQuery availability) {
    this.opportunities = opportunities;
    this.availability = availability;
  }

  public CatalogActor requireActor(CatalogActor actor) {
    return Objects.requireNonNull(actor, "actor");
  }

  public UUID requireCorrelation() {
    UUID correlationId = CorrelationContext.current();
    if (correlationId == null) {
      throw new CatalogValidationException("A correlação da solicitação é obrigatória.");
    }
    return correlationId;
  }

  public LoadedOpportunity load(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId) {
    CatalogHierarchy hierarchy =
        availability.requireEnvironmentHierarchy(publisherId, channelId, environmentId);
    ContextualOpportunity opportunity =
        opportunities
            .findByScope(publisherId, channelId, environmentId, opportunityId)
            .orElseThrow(ResourceNotFoundException::new);
    return new LoadedOpportunity(opportunity, hierarchy);
  }

  public record LoadedOpportunity(ContextualOpportunity opportunity, CatalogHierarchy hierarchy) {}
}
