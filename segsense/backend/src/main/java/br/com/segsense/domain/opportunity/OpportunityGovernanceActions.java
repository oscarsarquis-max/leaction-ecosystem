package br.com.segsense.domain.opportunity;

import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.Publisher;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public final class OpportunityGovernanceActions {

  private OpportunityGovernanceActions() {}

  public static List<GovernanceAction> available(
      ContextualOpportunity opportunity,
      Publisher publisher,
      Channel channel,
      ContextualEnvironment environment,
      Instant now) {
    List<GovernanceAction> actions = new ArrayList<>();
    boolean publishable = opportunity.effectivelyPublishable(publisher, channel, environment, now);
    boolean expired = PublicationWindow.isExpired(opportunity.current().content(), now);
    switch (opportunity.status()) {
      case DRAFT -> actions.add(GovernanceAction.SUBMIT);
      case UNDER_REVIEW -> {
        actions.add(GovernanceAction.RETURN_FOR_CHANGES);
        actions.add(GovernanceAction.APPROVE);
        actions.add(GovernanceAction.REJECT);
      }
      case APPROVED -> {
        if (publishable) {
          actions.add(GovernanceAction.ACTIVATE);
        }
        actions.add(GovernanceAction.REVOKE);
      }
      case PUBLISHED -> {
        actions.add(GovernanceAction.PAUSE);
        if (expired) {
          actions.add(GovernanceAction.EXPIRE);
        }
        actions.add(GovernanceAction.REVOKE);
      }
      case PAUSED -> {
        if (publishable) {
          actions.add(GovernanceAction.RESUME);
        }
        if (expired) {
          actions.add(GovernanceAction.EXPIRE);
        }
        actions.add(GovernanceAction.REVOKE);
      }
      case REVOKED, EXPIRED -> {
        // terminal
      }
    }
    return List.copyOf(actions);
  }
}
