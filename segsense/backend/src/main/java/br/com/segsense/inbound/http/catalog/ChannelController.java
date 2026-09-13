package br.com.segsense.inbound.http.catalog;

import br.com.segsense.application.catalog.CatalogAvailabilityQuery;
import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.application.catalog.CreateChannelUseCase;
import br.com.segsense.application.catalog.GetChannelUseCase;
import br.com.segsense.application.catalog.ListChannelsUseCase;
import br.com.segsense.application.catalog.RenameChannelUseCase;
import br.com.segsense.application.catalog.TransitionChannelStatusUseCase;
import br.com.segsense.domain.catalog.Channel;
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
@RequestMapping("/api/v1/admin/publishers/{publisherId}/channels")
public class ChannelController {

  private final CreateChannelUseCase createChannel;
  private final GetChannelUseCase getChannel;
  private final ListChannelsUseCase listChannels;
  private final RenameChannelUseCase renameChannel;
  private final TransitionChannelStatusUseCase transitionChannel;
  private final CatalogAvailabilityQuery availability;

  public ChannelController(
      CreateChannelUseCase createChannel,
      GetChannelUseCase getChannel,
      ListChannelsUseCase listChannels,
      RenameChannelUseCase renameChannel,
      TransitionChannelStatusUseCase transitionChannel,
      CatalogAvailabilityQuery availability) {
    this.createChannel = createChannel;
    this.getChannel = getChannel;
    this.listChannels = listChannels;
    this.renameChannel = renameChannel;
    this.transitionChannel = transitionChannel;
    this.availability = availability;
  }

  @PostMapping
  public ResponseEntity<ChannelResponse> create(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @RequestBody CreateChannelRequest request) {
    Channel channel =
        createChannel.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            request.key(),
            request.name(),
            CatalogHttpMapper.channelType(request.type()));
    Publisher publisher = availability.requirePublisher(publisherId);
    return ResponseEntity.created(
            URI.create(
                "/api/v1/admin/publishers/" + publisherId + "/channels/" + channel.id()))
        .body(CatalogHttpMapper.channel(channel, publisher));
  }

  @GetMapping("/{channelId}")
  public ChannelResponse get(@PathVariable UUID publisherId, @PathVariable UUID channelId) {
    Channel channel = getChannel.execute(publisherId, channelId);
    Publisher publisher = availability.requirePublisher(publisherId);
    return CatalogHttpMapper.channel(channel, publisher);
  }

  @GetMapping
  public CatalogCollectionResponse<ChannelResponse> list(
      @PathVariable UUID publisherId,
      @RequestParam(name = "page[size]", required = false) Integer pageSize,
      @RequestParam(name = "page[after]", required = false) String pageAfter) {
    CatalogPageQuery query = CatalogHttpMapper.pageQuery(pageSize, pageAfter);
    Publisher publisher = availability.requirePublisher(publisherId);
    return CatalogHttpMapper.collection(
        listChannels.execute(publisherId, query),
        channel -> CatalogHttpMapper.channel(channel, publisher));
  }

  @PatchMapping("/{channelId}")
  public ChannelResponse rename(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @RequestBody RenameResourceRequest request) {
    Channel channel =
        renameChannel.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            channelId,
            request.name(),
            CatalogHttpMapper.expectedVersion(request.version()));
    Publisher publisher = availability.requirePublisher(publisherId);
    return CatalogHttpMapper.channel(channel, publisher);
  }

  @PostMapping("/{channelId}/status")
  public ChannelResponse transition(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @RequestBody TransitionStatusRequest request) {
    Channel channel =
        transitionChannel.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            channelId,
            CatalogHttpMapper.status(request.status()),
            CatalogHttpMapper.expectedVersion(request.version()));
    Publisher publisher = availability.requirePublisher(publisherId);
    return CatalogHttpMapper.channel(channel, publisher);
  }
}
