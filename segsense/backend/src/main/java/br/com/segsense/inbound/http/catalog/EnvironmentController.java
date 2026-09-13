package br.com.segsense.inbound.http.catalog;

import br.com.segsense.application.catalog.CatalogAvailabilityQuery;
import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.application.catalog.CreateEnvironmentUseCase;
import br.com.segsense.application.catalog.GetChannelUseCase;
import br.com.segsense.application.catalog.GetEnvironmentUseCase;
import br.com.segsense.application.catalog.ListEnvironmentsUseCase;
import br.com.segsense.application.catalog.RenameEnvironmentUseCase;
import br.com.segsense.application.catalog.TransitionEnvironmentStatusUseCase;
import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.Publisher;
import java.net.URI;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments")
public class EnvironmentController {

  private final CreateEnvironmentUseCase createEnvironment;
  private final GetEnvironmentUseCase getEnvironment;
  private final ListEnvironmentsUseCase listEnvironments;
  private final RenameEnvironmentUseCase renameEnvironment;
  private final TransitionEnvironmentStatusUseCase transitionEnvironment;
  private final GetChannelUseCase getChannel;
  private final CatalogAvailabilityQuery availability;

  public EnvironmentController(
      CreateEnvironmentUseCase createEnvironment,
      GetEnvironmentUseCase getEnvironment,
      ListEnvironmentsUseCase listEnvironments,
      RenameEnvironmentUseCase renameEnvironment,
      TransitionEnvironmentStatusUseCase transitionEnvironment,
      GetChannelUseCase getChannel,
      CatalogAvailabilityQuery availability) {
    this.createEnvironment = createEnvironment;
    this.getEnvironment = getEnvironment;
    this.listEnvironments = listEnvironments;
    this.renameEnvironment = renameEnvironment;
    this.transitionEnvironment = transitionEnvironment;
    this.getChannel = getChannel;
    this.availability = availability;
  }

  @PostMapping
  public ResponseEntity<EnvironmentResponse> create(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @RequestBody CreateEnvironmentRequest request) {
    ContextualEnvironment environment =
        createEnvironment.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            channelId,
            request.key(),
            request.name(),
            CatalogHttpMapper.environmentType(request.type()),
            request.canonicalUrl());
    return ResponseEntity.created(
            URI.create(
                "/api/v1/admin/publishers/"
                    + publisherId
                    + "/channels/"
                    + channelId
                    + "/environments/"
                    + environment.id()))
        .body(toResponse(publisherId, channelId, environment));
  }

  @GetMapping("/{environmentId}")
  public EnvironmentResponse get(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId) {
    return toResponse(
        publisherId, channelId, getEnvironment.execute(publisherId, channelId, environmentId));
  }

  @GetMapping
  public CatalogCollectionResponse<EnvironmentResponse> list(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @RequestParam(name = "page[size]", required = false) Integer pageSize,
      @RequestParam(name = "page[after]", required = false) String pageAfter) {
    CatalogPageQuery query = CatalogHttpMapper.pageQuery(pageSize, pageAfter);
    Publisher publisher = availability.requirePublisher(publisherId);
    Channel channel = getChannel.execute(publisherId, channelId);
    return CatalogHttpMapper.collection(
        listEnvironments.execute(publisherId, channelId, query),
        environment -> CatalogHttpMapper.environment(environment, publisher, channel));
  }

  @PatchMapping("/{environmentId}")
  public EnvironmentResponse rename(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @RequestBody RenameResourceRequest request) {
    ContextualEnvironment environment =
        renameEnvironment.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            channelId,
            environmentId,
            request.name(),
            CatalogHttpMapper.expectedVersion(request.version()));
    return toResponse(publisherId, channelId, environment);
  }

  @PostMapping("/{environmentId}/status")
  public EnvironmentResponse transition(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @RequestBody TransitionStatusRequest request) {
    ContextualEnvironment environment =
        transitionEnvironment.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            channelId,
            environmentId,
            CatalogHttpMapper.status(request.status()),
            CatalogHttpMapper.expectedVersion(request.version()));
    return toResponse(publisherId, channelId, environment);
  }

  private EnvironmentResponse toResponse(
      UUID publisherId, UUID channelId, ContextualEnvironment environment) {
    Publisher publisher = availability.requirePublisher(publisherId);
    Channel channel = getChannel.execute(publisherId, channelId);
    return CatalogHttpMapper.environment(environment, publisher, channel);
  }
}
