package br.com.segsense.inbound.http.opportunity;

import br.com.segsense.application.catalog.CatalogAvailabilityQuery;
import br.com.segsense.application.catalog.CatalogAvailabilityQuery.CatalogHierarchy;
import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.application.opportunity.CreateOpportunityRevisionUseCase;
import br.com.segsense.application.opportunity.CreateOpportunityUseCase;
import br.com.segsense.application.opportunity.GetOpportunityRevisionUseCase;
import br.com.segsense.application.opportunity.GetOpportunityUseCase;
import br.com.segsense.application.opportunity.ListOpportunitiesUseCase;
import br.com.segsense.application.opportunity.ListOpportunityRevisionsUseCase;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.inbound.http.catalog.AuthenticatedCatalogActor;
import br.com.segsense.inbound.http.catalog.CatalogCollectionResponse;
import br.com.segsense.inbound.http.catalog.CatalogPageResponse;
import java.net.URI;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
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
    "/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities")
public class OpportunityController {

  private final CreateOpportunityUseCase createOpportunity;
  private final GetOpportunityUseCase getOpportunity;
  private final ListOpportunitiesUseCase listOpportunities;
  private final CreateOpportunityRevisionUseCase createRevision;
  private final ListOpportunityRevisionsUseCase listRevisions;
  private final GetOpportunityRevisionUseCase getRevision;
  private final CatalogAvailabilityQuery availability;
  private final Clock clock;

  public OpportunityController(
      CreateOpportunityUseCase createOpportunity,
      GetOpportunityUseCase getOpportunity,
      ListOpportunitiesUseCase listOpportunities,
      CreateOpportunityRevisionUseCase createRevision,
      ListOpportunityRevisionsUseCase listRevisions,
      GetOpportunityRevisionUseCase getRevision,
      CatalogAvailabilityQuery availability,
      Clock clock) {
    this.createOpportunity = createOpportunity;
    this.getOpportunity = getOpportunity;
    this.listOpportunities = listOpportunities;
    this.createRevision = createRevision;
    this.listRevisions = listRevisions;
    this.getRevision = getRevision;
    this.availability = availability;
    this.clock = clock;
  }

  @PostMapping
  public ResponseEntity<OpportunityResponse> create(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @RequestBody CreateOpportunityRequest request) {
    ContextualOpportunity opportunity =
        createOpportunity.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            channelId,
            environmentId,
            request.key(),
            OpportunityHttpMapper.content(
                request.title(),
                request.contextMode(),
                request.contextSummaryTemplate(),
                request.objectiveTemplate(),
                request.callToActionLabel(),
                request.validFrom(),
                request.validUntil(),
                request.contextFields()));
    return ResponseEntity.created(
            URI.create(
                "/api/v1/admin/publishers/"
                    + publisherId
                    + "/channels/"
                    + channelId
                    + "/environments/"
                    + environmentId
                    + "/opportunities/"
                    + opportunity.id()))
        .body(toResponse(publisherId, channelId, environmentId, opportunity));
  }

  @GetMapping
  public CatalogCollectionResponse<OpportunityResponse> list(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @RequestParam(name = "page[size]", required = false) Integer pageSize,
      @RequestParam(name = "page[after]", required = false) String pageAfter) {
    CatalogHierarchy hierarchy =
        availability.requireEnvironmentHierarchy(publisherId, channelId, environmentId);
    CatalogPageQuery query = OpportunityHttpMapper.pageQuery(pageSize, pageAfter);
    var page = listOpportunities.execute(publisherId, channelId, environmentId, query);
    List<OpportunityResponse> items =
        page.items().stream()
            .map(
                opportunity ->
                    mapOpportunity(hierarchy, opportunity))
            .toList();
    return new CatalogCollectionResponse<>(
        items, new CatalogPageResponse(page.size(), page.next()));
  }

  @GetMapping("/{opportunityId}")
  public OpportunityResponse get(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId) {
    return toResponse(
        publisherId,
        channelId,
        environmentId,
        getOpportunity.execute(publisherId, channelId, environmentId, opportunityId));
  }

  @PostMapping("/{opportunityId}/revisions")
  public OpportunityResponse createRevision(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody CreateOpportunityRevisionRequest request) {
    ContextualOpportunity opportunity =
        createRevision.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            channelId,
            environmentId,
            opportunityId,
            OpportunityHttpMapper.expectedVersion(request.expectedVersion()),
            OpportunityHttpMapper.baseRevision(request.baseRevision()),
            OpportunityHttpMapper.content(
                request.title(),
                request.contextMode(),
                request.contextSummaryTemplate(),
                request.objectiveTemplate(),
                request.callToActionLabel(),
                request.validFrom(),
                request.validUntil(),
                request.contextFields()));
    return toResponse(publisherId, channelId, environmentId, opportunity);
  }

  @GetMapping("/{opportunityId}/revisions")
  public CatalogCollectionResponse<OpportunityRevisionSnapshotResponse> listRevisions(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestParam(name = "page[size]", required = false) Integer pageSize,
      @RequestParam(name = "page[after]", required = false) String pageAfter) {
    getOpportunity.execute(publisherId, channelId, environmentId, opportunityId);
    var page =
        listRevisions.execute(
            publisherId,
            channelId,
            environmentId,
            opportunityId,
            OpportunityHttpMapper.pageQuery(pageSize, pageAfter));
    List<OpportunityRevisionSnapshotResponse> items =
        page.items().stream().map(OpportunityHttpMapper::snapshot).toList();
    return new CatalogCollectionResponse<>(
        items, new CatalogPageResponse(page.size(), page.next()));
  }

  @GetMapping("/{opportunityId}/revisions/{revisionNumber}")
  public OpportunityRevisionSnapshotResponse getRevision(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @PathVariable int revisionNumber) {
    return OpportunityHttpMapper.snapshot(
        getRevision.execute(
            publisherId, channelId, environmentId, opportunityId, revisionNumber));
  }

  private OpportunityResponse toResponse(
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      ContextualOpportunity opportunity) {
    CatalogHierarchy hierarchy =
        availability.requireEnvironmentHierarchy(publisherId, channelId, environmentId);
    return mapOpportunity(hierarchy, opportunity);
  }

  private OpportunityResponse mapOpportunity(
      CatalogHierarchy hierarchy, ContextualOpportunity opportunity) {
    Instant now = Instant.now(clock);
    return OpportunityHttpMapper.opportunity(
        opportunity,
        opportunity.effectivelyAvailable(
            hierarchy.publisher(), hierarchy.channel(), hierarchy.environment()),
        opportunity.effectivelyPublishable(
            hierarchy.publisher(), hierarchy.channel(), hierarchy.environment(), now),
        opportunity.effectivelyPublished(
            hierarchy.publisher(), hierarchy.channel(), hierarchy.environment(), now));
  }
}
