package br.com.segsense.application.link;

import br.com.segsense.application.catalog.CatalogActor;
import br.com.segsense.application.opportunity.OpportunityCommandSupport;
import br.com.segsense.domain.link.OpportunityNotPublishedException;
import br.com.segsense.domain.link.PublishedContextLink;
import br.com.segsense.domain.link.PublisherBindingDraft;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IssueContextLinkUseCase {

  private final OpportunityCommandSupport support;
  private final PublishedContextLinkRepository links;
  private final OpaqueTokenGenerator tokens;
  private final PublicContextUrl publicUrls;
  private final LinkTtlSettings ttl;
  private final Clock clock;

  public IssueContextLinkUseCase(
      OpportunityCommandSupport support,
      PublishedContextLinkRepository links,
      OpaqueTokenGenerator tokens,
      PublicContextUrl publicUrls,
      LinkTtlSettings ttl,
      Clock clock) {
    this.support = support;
    this.links = links;
    this.tokens = tokens;
    this.publicUrls = publicUrls;
    this.ttl = ttl;
    this.clock = clock;
  }

  @Transactional
  public IssuedContextLink execute(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      String placementKey,
      String label,
      Instant expiresAt,
      List<PublisherBindingDraft> publisherContext) {
    CatalogActor required = support.requireActor(actor);
    UUID correlationId = support.requireCorrelation();
    OpportunityCommandSupport.LoadedOpportunity loaded =
        support.load(publisherId, channelId, environmentId, opportunityId);
    ContextualOpportunity opportunity = loaded.opportunity();
    Instant now = clock.instant();
    if (!opportunity.effectivelyPublished(
        loaded.hierarchy().publisher(),
        loaded.hierarchy().channel(),
        loaded.hierarchy().environment(),
        now)) {
      throw new OpportunityNotPublishedException();
    }
    String rawToken = tokens.generate();
    PublishedContextLink.IssuedLink issued =
        PublishedContextLink.issue(
            UUID.randomUUID(),
            opportunity,
            placementKey,
            label,
            expiresAt,
            ttl.latestAllowed(now),
            now,
            required.subjectId(),
            correlationId,
            rawToken,
            publisherContext);
    PublishedContextLink persisted = links.saveNew(issued.link(), issued.event());
    return new IssuedContextLink(
        persisted, rawToken, publicUrls.publicUrl(rawToken), persisted.effectiveStatus(now));
  }

  public record IssuedContextLink(
      PublishedContextLink link,
      String rawToken,
      String publicUrl,
      br.com.segsense.domain.link.EffectiveLinkStatus effectiveStatus) {}
}
