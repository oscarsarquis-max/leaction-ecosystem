package br.com.segsense.inbound.http.consent;

import br.com.segsense.application.consent.ManageContextInstanceUseCase;
import br.com.segsense.application.consent.ManageContextInstanceUseCase.CollectedValueDraft;
import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.consent.InstanceCredentialRequiredException;
import br.com.segsense.inbound.http.link.NonStoreHeaders;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/public/context-links/{opaqueToken}/context-instances")
public class PublicContextInstanceController {

  public static final String CREDENTIAL_HEADER = ManageContextInstanceUseCase.CREDENTIAL_HEADER;
  public static final String IDEMPOTENCY_HEADER = "Idempotency-Key";

  private final ManageContextInstanceUseCase instances;

  public PublicContextInstanceController(ManageContextInstanceUseCase instances) {
    this.instances = instances;
  }

  @PostMapping
  public ResponseEntity<ContextInstanceResponse> create(
      @PathVariable String opaqueToken,
      @RequestHeader(value = IDEMPOTENCY_HEADER, required = false) String idempotencyKey) {
    var created = instances.create(opaqueToken, idempotencyKey);
    return ResponseEntity.status(201)
        .headers(NonStoreHeaders.of())
        .body(ContextInstanceResponse.from(created.instance(), created.rawCredential()));
  }

  @GetMapping("/current")
  public ResponseEntity<ContextInstanceResponse> current(
      @PathVariable String opaqueToken,
      @RequestHeader(value = CREDENTIAL_HEADER, required = false) String credential) {
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(ContextInstanceResponse.from(instances.current(opaqueToken, require(credential)), null));
  }

  @PutMapping("/current/values")
  public ResponseEntity<ContextInstanceResponse> values(
      @PathVariable String opaqueToken,
      @RequestHeader(value = CREDENTIAL_HEADER, required = false) String credential,
      @RequestBody ContextInstanceValuesRequest request) {
    List<CollectedValueDraft> drafts =
        request == null || request.values() == null
            ? List.of()
            : request.values().stream()
                .map(item -> new CollectedValueDraft(item.key(), item.type(), item.value()))
                .toList();
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            ContextInstanceResponse.from(
                instances.putValues(
                    opaqueToken, require(credential), expected(request == null ? null : request.expectedVersion()), drafts),
                null));
  }

  @PostMapping("/current/authorize")
  public ResponseEntity<ContextInstanceResponse> authorize(
      @PathVariable String opaqueToken,
      @RequestHeader(value = CREDENTIAL_HEADER, required = false) String credential,
      @RequestBody ContextInstanceDecisionRequest request) {
    boolean acknowledged = request != null && Boolean.TRUE.equals(request.acknowledged());
    int noticeVersion = request == null || request.noticeVersion() == null ? -1 : request.noticeVersion();
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            ContextInstanceResponse.from(
                instances.authorize(
                    opaqueToken,
                    require(credential),
                    expected(request == null ? null : request.expectedVersion()),
                    noticeVersion,
                    acknowledged),
                null));
  }

  @PostMapping("/current/withdraw")
  public ResponseEntity<ContextInstanceResponse> withdraw(
      @PathVariable String opaqueToken,
      @RequestHeader(value = CREDENTIAL_HEADER, required = false) String credential,
      @RequestBody ContextInstanceDecisionRequest request) {
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            ContextInstanceResponse.from(
                instances.withdraw(
                    opaqueToken,
                    require(credential),
                    expected(request == null ? null : request.expectedVersion())),
                null));
  }

  private static String require(String credential) {
    if (credential == null || credential.isBlank()) {
      throw new InstanceCredentialRequiredException();
    }
    return credential.trim();
  }

  private static long expected(Long expectedVersion) {
    if (expectedVersion == null) {
      throw new CatalogValidationException("A versão esperada é obrigatória.");
    }
    return expectedVersion;
  }
}
