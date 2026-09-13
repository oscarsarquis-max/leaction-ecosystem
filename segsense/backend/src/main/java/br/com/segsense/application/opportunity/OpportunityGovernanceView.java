package br.com.segsense.application.opportunity;

import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.GovernanceAction;
import br.com.segsense.domain.opportunity.OpportunityDecision;
import br.com.segsense.domain.opportunity.OpportunitySubmission;
import java.util.List;

public record OpportunityGovernanceView(
    ContextualOpportunity opportunity,
    OpportunitySubmission openSubmission,
    OpportunityDecision latestDecision,
    boolean effectivelyAvailable,
    boolean effectivelyPublishable,
    boolean effectivelyPublished,
    boolean windowOpen,
    boolean windowExpired,
    List<GovernanceAction> availableActions) {

  public OpportunityGovernanceView {
    availableActions = List.copyOf(availableActions);
  }
}
