package br.com.segsense.application.link;

import br.com.segsense.application.catalog.CatalogPage;
import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.application.opportunity.OpportunityCommandSupport;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.link.ContextLinkEvent;
import br.com.segsense.domain.link.PublishedContextLink;
import java.time.Clock;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class QueryContextLinksUseCase {

  private final OpportunityCommandSupport support;
  private final PublishedContextLinkRepository links;
  private final Clock clock;

  public QueryContextLinksUseCase(
      OpportunityCommandSupport support, PublishedContextLinkRepository links, Clock clock) {
    this.support = support;
    this.links = links;
    this.clock = clock;
  }

  @Transactional(readOnly = true)
  public CatalogPage<PublishedContextLink> list(
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      CatalogPageQuery query) {
    OpportunityCommandSupport.LoadedOpportunity loaded =
        support.load(publisherId, channelId, environmentId, opportunityId);
    boolean hasCursor = query.after() != null;
    ContextLinkCursor cursor = hasCursor ? ContextLinkCursor.decode(query.after()) : null;
    List<PublishedContextLink> fetched =
        links.listAfter(
            loaded.opportunity().id(),
            hasCursor
                ? new PublishedContextLinkRepository.InstantCursor(cursor.issuedAt(), cursor.id())
                : null,
            hasCursor,
            query.size() + 1);
    return page(fetched, query, true);
  }

  @Transactional(readOnly = true)
  public PublishedContextLink get(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId, UUID linkId) {
    support.load(publisherId, channelId, environmentId, opportunityId);
    return links
        .findByScope(publisherId, channelId, environmentId, opportunityId, linkId)
        .orElseThrow(ResourceNotFoundException::new);
  }

  @Transactional(readOnly = true)
  public CatalogPage<ContextLinkEvent> events(
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      UUID linkId,
      CatalogPageQuery query) {
    get(publisherId, channelId, environmentId, opportunityId, linkId);
    boolean hasCursor = query.after() != null;
    ContextLinkCursor cursor = hasCursor ? ContextLinkCursor.decode(query.after()) : null;
    List<ContextLinkEvent> fetched =
        links.listEventsAfter(
            linkId,
            hasCursor
                ? new PublishedContextLinkRepository.InstantCursor(cursor.issuedAt(), cursor.id())
                : null,
            hasCursor,
            query.size() + 1);
    boolean hasNext = fetched.size() > query.size();
    List<ContextLinkEvent> items =
        new ArrayList<>(hasNext ? fetched.subList(0, query.size()) : fetched);
    String next = null;
    if (hasNext && !items.isEmpty()) {
      ContextLinkEvent last = items.get(items.size() - 1);
      next = ContextLinkCursor.encode(last.occurredAt(), last.id());
    }
    return new CatalogPage<>(items, next, query.size());
  }

  public java.time.Instant now() {
    return clock.instant();
  }

  private static CatalogPage<PublishedContextLink> page(
      List<PublishedContextLink> fetched, CatalogPageQuery query, boolean issuedDesc) {
    boolean hasNext = fetched.size() > query.size();
    List<PublishedContextLink> items =
        new ArrayList<>(hasNext ? fetched.subList(0, query.size()) : fetched);
    String next = null;
    if (hasNext && !items.isEmpty()) {
      PublishedContextLink last = items.get(items.size() - 1);
      next = ContextLinkCursor.encode(last.issuedAt(), last.id());
    }
    return new CatalogPage<>(items, next, query.size());
  }
}
