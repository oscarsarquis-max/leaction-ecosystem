package br.com.segsense.inbound.http.consent;

import br.com.segsense.application.consent.ManageConsentNoticeUseCase;
import br.com.segsense.domain.consent.ConsentNoticeContent;
import br.com.segsense.inbound.http.catalog.AuthenticatedCatalogActor;
import br.com.segsense.inbound.http.link.NonStoreHeaders;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(
    "/api/v1/admin/publishers/{publisherId}/channels/{channelId}/environments/{environmentId}/opportunities/{opportunityId}/consent-notice")
public class ConsentNoticeAdminController {

  private final ManageConsentNoticeUseCase notices;

  public ConsentNoticeAdminController(ManageConsentNoticeUseCase notices) {
    this.notices = notices;
  }

  @GetMapping
  public ResponseEntity<ConsentNoticeResponse> get(
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId) {
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            ConsentNoticeResponse.from(
                notices.get(publisherId, channelId, environmentId, opportunityId)));
  }

  @PostMapping
  public ResponseEntity<ConsentNoticeResponse> create(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody ConsentNoticeRequest request) {
    return ResponseEntity.status(201)
        .headers(NonStoreHeaders.of())
        .body(
            ConsentNoticeResponse.from(
                notices.create(
                    AuthenticatedCatalogActor.from(authentication),
                    publisherId,
                    channelId,
                    environmentId,
                    opportunityId,
                    content(request))));
  }

  @PostMapping("/draft")
  public ResponseEntity<ConsentNoticeResponse> editDraft(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody ConsentNoticeRequest request) {
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            ConsentNoticeResponse.from(
                notices.editDraft(
                    AuthenticatedCatalogActor.from(authentication),
                    publisherId,
                    channelId,
                    environmentId,
                    opportunityId,
                    expected(request),
                    content(request))));
  }

  @PostMapping("/approve")
  public ResponseEntity<ConsentNoticeResponse> approve(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody ConsentNoticeRequest request) {
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            ConsentNoticeResponse.from(
                notices.approve(
                    AuthenticatedCatalogActor.from(authentication),
                    publisherId,
                    channelId,
                    environmentId,
                    opportunityId,
                    expected(request),
                    request == null ? null : request.justification())));
  }

  @PostMapping("/retire")
  public ResponseEntity<ConsentNoticeResponse> retire(
      Authentication authentication,
      @PathVariable UUID publisherId,
      @PathVariable UUID channelId,
      @PathVariable UUID environmentId,
      @PathVariable UUID opportunityId,
      @RequestBody ConsentNoticeRequest request) {
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            ConsentNoticeResponse.from(
                notices.retire(
                    AuthenticatedCatalogActor.from(authentication),
                    publisherId,
                    channelId,
                    environmentId,
                    opportunityId,
                    expected(request),
                    request == null ? null : request.justification())));
  }

  private static ConsentNoticeContent content(ConsentNoticeRequest request) {
    if (request == null) {
      return ConsentNoticeContent.parse(null, null, null, null);
    }
    return ConsentNoticeContent.parse(
        request.purposeTitle(),
        request.purposeDescription(),
        request.transparencyText(),
        request.noExternalSharingText());
  }

  private static long expected(ConsentNoticeRequest request) {
    if (request == null || request.expectedVersion() == null) {
      throw new br.com.segsense.domain.catalog.CatalogValidationException(
          "A versão esperada é obrigatória.");
    }
    return request.expectedVersion();
  }
}
