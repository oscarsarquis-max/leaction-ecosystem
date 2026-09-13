package br.com.segsense.inbound.http.link;

import br.com.segsense.application.catalog.CatalogPage;
import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.application.link.IssueContextLinkUseCase;
import br.com.segsense.application.link.QueryContextLinksUseCase;
import br.com.segsense.application.link.RevokeContextLinkUseCase;
import br.com.segsense.domain.link.ContextLinkEvent;
import br.com.segsense.domain.link.PublishedContextLink;
import br.com.segsense.inbound.http.catalog.AuthenticatedCatalogActor;
import br.com.segsense.inbound.http.catalog.CatalogCollectionResponse;
import br.com.segsense.inbound.http.catalog.CatalogPageResponse;
import java.net.URI;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(
    "/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities/{opportunityId}/links")
public class ContextLinkAdminController {

  private final IssueContextLinkUseCase issue;
  private final RevokeContextLinkUseCase revoke;
  private final QueryContextLinksUseCase query;

  public ContextLinkAdminController(
      IssueContextLinkUseCase issue,
      RevokeContextLinkUseCase revoke,
      QueryContextLinksUseCase query) {
    this.issue = issue;
    this.revoke = revoke;
    this.query = query;
  }

  @PostMapping
  public ResponseEntity<IssuedContextLinkResponse> issue(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody IssueContextLinkRequest request) {
    IssueContextLinkUseCase.IssuedContextLink issued =
        issue.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            channelId,
            environmentId,
            opportunityId,
            request.placementKey(),
            request.label(),
            ContextLinkHttpMapper.expiresAt(request.expiresAt()),
            ContextLinkHttpMapper.bindings(request.publisherContext()));
    IssuedContextLinkResponse body = ContextLinkHttpMapper.issued(issued);
    return ResponseEntity.status(HttpStatus.CREATED)
        .headers(NonStoreHeaders.of())
        .location(
            URI.create(
                "/api/v1/admin/publishers/"
                    + publisherId
                    + "/channels/"
                    + channelId
                    + "/environments/"
                    + environmentId
                    + "/opportunities/"
                    + opportunityId
                    + "/links/"
                    + issued.link().id()))
        .body(body);
  }

  @GetMapping
  public ResponseEntity<CatalogCollectionResponse<ContextLinkResponse>> list(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestParam(name = "page[size]", required = false) Integer pageSize,
      @RequestParam(name = "page[after]", required = false) String pageAfter) {
    CatalogPageQuery pageQuery = ContextLinkHttpMapper.pageQuery(pageSize, pageAfter);
    CatalogPage<PublishedContextLink> page =
        query.list(publisherId, channelId, environmentId, opportunityId, pageQuery);
    List<ContextLinkResponse> items =
        page.items().stream()
            .map(link -> ContextLinkHttpMapper.metadata(link, query.now()))
            .toList();
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            new CatalogCollectionResponse<>(
                items, new CatalogPageResponse(page.size(), page.next())));
  }

  @GetMapping("/{linkId}")
  public ResponseEntity<ContextLinkResponse> get(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @PathVariable UUID linkId) {
    PublishedContextLink link =
        query.get(publisherId, channelId, environmentId, opportunityId, linkId);
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(ContextLinkHttpMapper.metadata(link, query.now()));
  }

  @PostMapping("/{linkId}/revoke")
  public ResponseEntity<ContextLinkResponse> revoke(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @PathVariable UUID linkId,
      @RequestBody RevokeContextLinkRequest request) {
    PublishedContextLink link =
        revoke.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            channelId,
            environmentId,
            opportunityId,
            linkId,
            ContextLinkHttpMapper.expectedVersion(request.expectedVersion()),
            request.justification());
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(ContextLinkHttpMapper.metadata(link, query.now()));
  }

  @GetMapping("/{linkId}/events")
  public ResponseEntity<CatalogCollectionResponse<ContextLinkEventResponse>> events(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @PathVariable UUID linkId,
      @RequestParam(name = "page[size]", required = false) Integer pageSize,
      @RequestParam(name = "page[after]", required = false) String pageAfter) {
    CatalogPage<ContextLinkEvent> page =
        query.events(
            publisherId,
            channelId,
            environmentId,
            opportunityId,
            linkId,
            ContextLinkHttpMapper.pageQuery(pageSize, pageAfter));
    List<ContextLinkEventResponse> items =
        page.items().stream().map(ContextLinkHttpMapper::event).toList();
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            new CatalogCollectionResponse<>(
                items, new CatalogPageResponse(page.size(), page.next())));
  }
}
