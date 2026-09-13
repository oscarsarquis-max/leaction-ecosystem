package br.com.segsense.inbound.http.catalog;

import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.application.catalog.CreatePublisherUseCase;
import br.com.segsense.application.catalog.GetPublisherUseCase;
import br.com.segsense.application.catalog.ListPublishersUseCase;
import br.com.segsense.application.catalog.RenamePublisherUseCase;
import br.com.segsense.application.catalog.TransitionPublisherStatusUseCase;
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
@RequestMapping("/api/v1/admin/publishers")
public class PublisherController {

  private final CreatePublisherUseCase createPublisher;
  private final GetPublisherUseCase getPublisher;
  private final ListPublishersUseCase listPublishers;
  private final RenamePublisherUseCase renamePublisher;
  private final TransitionPublisherStatusUseCase transitionPublisher;

  public PublisherController(
      CreatePublisherUseCase createPublisher,
      GetPublisherUseCase getPublisher,
      ListPublishersUseCase listPublishers,
      RenamePublisherUseCase renamePublisher,
      TransitionPublisherStatusUseCase transitionPublisher) {
    this.createPublisher = createPublisher;
    this.getPublisher = getPublisher;
    this.listPublishers = listPublishers;
    this.renamePublisher = renamePublisher;
    this.transitionPublisher = transitionPublisher;
  }

  @PostMapping
  public ResponseEntity<PublisherResponse> create(
      Authentication authentication, @RequestBody CreatePublisherRequest request) {
    Publisher publisher =
        createPublisher.execute(
            AuthenticatedCatalogActor.from(authentication), request.key(), request.name());
    return ResponseEntity.created(URI.create("/api/v1/admin/publishers/" + publisher.id()))
        .body(CatalogHttpMapper.publisher(publisher));
  }

  @GetMapping("/{publisherId}")
  public PublisherResponse get(@PathVariable UUID publisherId) {
    return CatalogHttpMapper.publisher(getPublisher.execute(publisherId));
  }

  @GetMapping
  public CatalogCollectionResponse<PublisherResponse> list(
      @RequestParam(name = "page[size]", required = false) Integer pageSize,
      @RequestParam(name = "page[after]", required = false) String pageAfter) {
    CatalogPageQuery query = CatalogHttpMapper.pageQuery(pageSize, pageAfter);
    return CatalogHttpMapper.collection(listPublishers.execute(query), CatalogHttpMapper::publisher);
  }

  @PatchMapping("/{publisherId}")
  public PublisherResponse rename(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @RequestBody RenameResourceRequest request) {
    return CatalogHttpMapper.publisher(
        renamePublisher.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            request.name(),
            CatalogHttpMapper.expectedVersion(request.version())));
  }

  @PostMapping("/{publisherId}/status")
  public PublisherResponse transition(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @RequestBody TransitionStatusRequest request) {
    return CatalogHttpMapper.publisher(
        transitionPublisher.execute(
            AuthenticatedCatalogActor.from(authentication),
            publisherId,
            CatalogHttpMapper.status(request.status()),
            CatalogHttpMapper.expectedVersion(request.version())));
  }
}
