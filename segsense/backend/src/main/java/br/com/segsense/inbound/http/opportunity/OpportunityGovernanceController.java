package br.com.segsense.inbound.http.opportunity;

import br.com.segsense.application.opportunity.GetOpportunityGovernanceUseCase;
import br.com.segsense.application.opportunity.ListOpportunityLifecycleEventsUseCase;
import br.com.segsense.application.opportunity.ManagePublicationUseCase;
import br.com.segsense.application.opportunity.ReviewOpportunityUseCase;
import br.com.segsense.application.opportunity.SubmitOpportunityUseCase;
import br.com.segsense.domain.opportunity.DecisionOutcome;
import br.com.segsense.domain.opportunity.LifecycleEventType;
import br.com.segsense.inbound.http.catalog.AuthenticatedCatalogActor;
import br.com.segsense.inbound.http.catalog.CatalogCollectionResponse;
import br.com.segsense.inbound.http.catalog.CatalogPageResponse;
import java.util.List;
import java.util.UUID;
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
    "/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities/{opportunityId}")
public class OpportunityGovernanceController {

  private final SubmitOpportunityUseCase submit;
  private final ReviewOpportunityUseCase review;
  private final ManagePublicationUseCase publication;
  private final GetOpportunityGovernanceUseCase getGovernance;
  private final ListOpportunityLifecycleEventsUseCase listEvents;

  public OpportunityGovernanceController(
      SubmitOpportunityUseCase submit,
      ReviewOpportunityUseCase review,
      ManagePublicationUseCase publication,
      GetOpportunityGovernanceUseCase getGovernance,
      ListOpportunityLifecycleEventsUseCase listEvents) {
    this.submit = submit;
    this.review = review;
    this.publication = publication;
    this.getGovernance = getGovernance;
    this.listEvents = listEvents;
  }

  @GetMapping("/governance")
  public OpportunityGovernanceResponse get(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId) {
    return OpportunityHttpMapper.governance(
        getGovernance.execute(publisherId, channelId, environmentId, opportunityId));
  }

  @GetMapping("/governance/events")
  public CatalogCollectionResponse<LifecycleEventResponse> events(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestParam(name = "page[size]", required = false) Integer pageSize,
      @RequestParam(name = "page[after]", required = false) String pageAfter) {
    var page =
        listEvents.execute(
            publisherId,
            channelId,
            environmentId,
            opportunityId,
            OpportunityHttpMapper.pageQuery(pageSize, pageAfter));
    List<LifecycleEventResponse> items =
        page.items().stream().map(OpportunityHttpMapper::event).toList();
    return new CatalogCollectionResponse<>(
        items, new CatalogPageResponse(page.size(), page.next()));
  }

  @PostMapping("/governance/submit")
  public OpportunityGovernanceResponse submit(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody GovernanceCommandRequest request) {
    submit.execute(
        AuthenticatedCatalogActor.from(authentication),
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        OpportunityHttpMapper.expectedVersion(request.expectedVersion()));
    return get(publisherId, channelId, environmentId, opportunityId);
  }

  @PostMapping("/governance/return-for-changes")
  public OpportunityGovernanceResponse returnForChanges(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody GovernanceCommandRequest request) {
    review.execute(
        AuthenticatedCatalogActor.from(authentication),
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        OpportunityHttpMapper.expectedVersion(request.expectedVersion()),
        OpportunityHttpMapper.revisionNumber(request.revisionNumber()),
        DecisionOutcome.RETURNED,
        request.justification());
    return get(publisherId, channelId, environmentId, opportunityId);
  }

  @PostMapping("/governance/approve")
  public OpportunityGovernanceResponse approve(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody GovernanceCommandRequest request) {
    review.execute(
        AuthenticatedCatalogActor.from(authentication),
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        OpportunityHttpMapper.expectedVersion(request.expectedVersion()),
        OpportunityHttpMapper.revisionNumber(request.revisionNumber()),
        DecisionOutcome.APPROVED,
        null);
    return get(publisherId, channelId, environmentId, opportunityId);
  }

  @PostMapping("/governance/reject")
  public OpportunityGovernanceResponse reject(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody GovernanceCommandRequest request) {
    review.execute(
        AuthenticatedCatalogActor.from(authentication),
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        OpportunityHttpMapper.expectedVersion(request.expectedVersion()),
        OpportunityHttpMapper.revisionNumber(request.revisionNumber()),
        DecisionOutcome.REJECTED,
        request.justification());
    return get(publisherId, channelId, environmentId, opportunityId);
  }

  @PostMapping("/publication/activate")
  public OpportunityGovernanceResponse activate(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody GovernanceCommandRequest request) {
    return publication(
        authentication,
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        request,
        LifecycleEventType.ACTIVATED);
  }

  @PostMapping("/publication/pause")
  public OpportunityGovernanceResponse pause(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody GovernanceCommandRequest request) {
    return publication(
        authentication,
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        request,
        LifecycleEventType.PAUSED);
  }

  @PostMapping("/publication/resume")
  public OpportunityGovernanceResponse resume(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody GovernanceCommandRequest request) {
    return publication(
        authentication,
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        request,
        LifecycleEventType.RESUMED);
  }

  @PostMapping("/publication/expire")
  public OpportunityGovernanceResponse expire(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody GovernanceCommandRequest request) {
    return publication(
        authentication,
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        request,
        LifecycleEventType.EXPIRED);
  }

  @PostMapping("/publication/revoke")
  public OpportunityGovernanceResponse revoke(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody GovernanceCommandRequest request) {
    return publication(
        authentication,
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        request,
        LifecycleEventType.REVOKED);
  }

  private OpportunityGovernanceResponse publication(
      Authentication authentication,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      GovernanceCommandRequest request,
      LifecycleEventType command) {
    publication.execute(
        AuthenticatedCatalogActor.from(authentication),
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        OpportunityHttpMapper.expectedVersion(request.expectedVersion()),
        command,
        request.justification());
    return get(publisherId, channelId, environmentId, opportunityId);
  }
}
