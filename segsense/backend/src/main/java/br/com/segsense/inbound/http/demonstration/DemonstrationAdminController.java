package br.com.segsense.inbound.http.demonstration;

import br.com.segsense.application.demonstration.ManageDemonstrationStoryUseCase;
import br.com.segsense.inbound.http.catalog.AuthenticatedCatalogActor;
import java.net.URI;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/admin/demonstrations")
public class DemonstrationAdminController {

  private final ManageDemonstrationStoryUseCase manage;

  public DemonstrationAdminController(ManageDemonstrationStoryUseCase manage) {
    this.manage = manage;
  }

  @GetMapping
  public List<DemonstrationAdminResponse> list() {
    return manage.list().stream().map(story -> DemonstrationHttpMapper.story(story, true)).toList();
  }

  @GetMapping("/sources")
  public List<DemonstrationSourceResponse> sources() {
    return manage.sources().stream().map(DemonstrationHttpMapper::source).toList();
  }

  @GetMapping("/{key}")
  public DemonstrationAdminResponse get(@PathVariable String key) {
    return DemonstrationHttpMapper.story(manage.get(key), true);
  }

  @PostMapping
  public ResponseEntity<DemonstrationAdminResponse> create(
      Authentication authentication, @RequestBody CreateDemonstrationRequest request) {
    var story =
        manage.create(
            AuthenticatedCatalogActor.from(authentication), request.key(), DemonstrationHttpMapper.draft(request));
    return ResponseEntity.created(URI.create("/api/v1/admin/demonstrations/" + story.key().value()))
        .body(DemonstrationHttpMapper.story(story, true));
  }

  @PostMapping("/{key}/draft")
  public DemonstrationAdminResponse updateDraft(
      Authentication authentication,
      @PathVariable String key,
      @RequestBody DemonstrationDraftRequest request) {
    return DemonstrationHttpMapper.story(
        manage.updateDraft(
            AuthenticatedCatalogActor.from(authentication),
            key,
            DemonstrationHttpMapper.expectedVersion(request.version()),
            DemonstrationHttpMapper.draft(request)),
        true);
  }

  @PostMapping("/{key}/submit")
  public DemonstrationAdminResponse submit(
      Authentication authentication,
      @PathVariable String key,
      @RequestBody DemonstrationDraftRequest request) {
    return DemonstrationHttpMapper.story(
        manage.submit(
            AuthenticatedCatalogActor.from(authentication),
            key,
            DemonstrationHttpMapper.expectedVersion(request.version()),
            request.justification()),
        true);
  }

  @PostMapping("/{key}/return")
  public DemonstrationAdminResponse returnForChanges(
      Authentication authentication,
      @PathVariable String key,
      @RequestBody DemonstrationDraftRequest request) {
    return DemonstrationHttpMapper.story(
        manage.returnForChanges(
            AuthenticatedCatalogActor.from(authentication),
            key,
            DemonstrationHttpMapper.expectedVersion(request.version()),
            request.justification(),
            DemonstrationHttpMapper.draft(request)),
        true);
  }

  @PostMapping("/{key}/approve")
  public DemonstrationAdminResponse approve(
      Authentication authentication,
      @PathVariable String key,
      @RequestBody DemonstrationDraftRequest request) {
    return DemonstrationHttpMapper.story(
        manage.approve(
            AuthenticatedCatalogActor.from(authentication),
            key,
            DemonstrationHttpMapper.expectedVersion(request.version()),
            request.justification()),
        true);
  }

  @PostMapping("/{key}/publish")
  public DemonstrationAdminResponse publish(
      Authentication authentication,
      @PathVariable String key,
      @RequestBody DemonstrationDraftRequest request) {
    return DemonstrationHttpMapper.story(
        manage.publish(
            AuthenticatedCatalogActor.from(authentication),
            key,
            DemonstrationHttpMapper.expectedVersion(request.version()),
            request.justification()),
        true);
  }

  @PostMapping("/{key}/pause")
  public DemonstrationAdminResponse pause(
      Authentication authentication,
      @PathVariable String key,
      @RequestBody DemonstrationDraftRequest request) {
    return DemonstrationHttpMapper.story(
        manage.pause(
            AuthenticatedCatalogActor.from(authentication),
            key,
            DemonstrationHttpMapper.expectedVersion(request.version()),
            request.justification()),
        true);
  }

  @PostMapping("/{key}/resume")
  public DemonstrationAdminResponse resume(
      Authentication authentication,
      @PathVariable String key,
      @RequestBody DemonstrationDraftRequest request) {
    return DemonstrationHttpMapper.story(
        manage.resume(
            AuthenticatedCatalogActor.from(authentication),
            key,
            DemonstrationHttpMapper.expectedVersion(request.version()),
            request.justification()),
        true);
  }

  @PostMapping("/{key}/retire")
  public DemonstrationAdminResponse retire(
      Authentication authentication,
      @PathVariable String key,
      @RequestBody DemonstrationDraftRequest request) {
    return DemonstrationHttpMapper.story(
        manage.retire(
            AuthenticatedCatalogActor.from(authentication),
            key,
            DemonstrationHttpMapper.expectedVersion(request.version()),
            request.justification()),
        true);
  }

  @PostMapping("/{key}/revisions")
  public DemonstrationAdminResponse newRevision(
      Authentication authentication,
      @PathVariable String key,
      @RequestBody DemonstrationDraftRequest request) {
    return DemonstrationHttpMapper.story(
        manage.newDraft(
            AuthenticatedCatalogActor.from(authentication),
            key,
            DemonstrationHttpMapper.expectedVersion(request.version()),
            DemonstrationHttpMapper.draft(request)),
        true);
  }
}
