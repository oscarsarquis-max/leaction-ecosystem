package br.com.segsense.inbound.http.link;

import br.com.segsense.application.link.ResolvePublicContextLinkUseCase;
import br.com.segsense.application.link.ResolvePublicContextLinkUseCase.PublicContextEnvelope;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/public/context-links")
public class PublicContextLinkController {

  private final ResolvePublicContextLinkUseCase resolve;

  public PublicContextLinkController(ResolvePublicContextLinkUseCase resolve) {
    this.resolve = resolve;
  }

  @GetMapping("/{opaqueToken}")
  public ResponseEntity<PublicContextLinkResponse> resolve(@PathVariable String opaqueToken) {
    PublicContextEnvelope envelope = resolve.execute(opaqueToken);
    return ResponseEntity.ok()
        .headers(NonStoreHeaders.of())
        .body(
            new PublicContextLinkResponse(
                envelope.applicationId(),
                envelope.resolutionId(),
                envelope.title(),
                envelope.callToActionLabel(),
                envelope.contextMode(),
                new PublicContextLinkResponse.ContextSummary(
                    envelope.contextSummary().template(),
                    envelope.contextSummary().publisherValues()),
                envelope.publisherBindings().stream()
                    .map(
                        binding ->
                            new PublicContextLinkResponse.PublisherBinding(
                                binding.fieldKey(),
                                binding.label(),
                                binding.type(),
                                binding.value()))
                    .toList(),
                envelope.userFields().stream()
                    .map(
                        field ->
                            new PublicContextLinkResponse.UserField(
                                field.key(),
                                field.label(),
                                field.type(),
                                field.required(),
                                field.allowedValues()))
                    .toList(),
                envelope.effectiveValidFrom(),
                envelope.effectiveValidUntil(),
                envelope.quotationPerformed(),
                envelope.eligibilityEvaluated(),
                envelope.recommendationPerformed(),
                new PublicContextLinkResponse.Continuity(
                    envelope.continuity().available(),
                    envelope.continuity().noticeVersion(),
                    envelope.continuity().purposeTitle(),
                    envelope.continuity().purposeDescription(),
                    envelope.continuity().transparencyText(),
                    envelope.continuity().noExternalSharingStatement())));
  }
}
