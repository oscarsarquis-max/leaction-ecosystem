package br.com.segsense.inbound.http.demonstration;

import br.com.segsense.application.demonstration.GetPublishedDemonstrationUseCase;
import br.com.segsense.inbound.http.link.NonStoreHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/public/demonstrations")
public class PublicDemonstrationController {

  private final GetPublishedDemonstrationUseCase published;

  public PublicDemonstrationController(GetPublishedDemonstrationUseCase published) {
    this.published = published;
  }

  @GetMapping("/{key}")
  public ResponseEntity<PublicDemonstrationResponse> get(@PathVariable String key) {
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(DemonstrationHttpMapper.published(published.execute(key)));
  }
}
