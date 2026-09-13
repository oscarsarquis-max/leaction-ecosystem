package br.com.segsense.application.link;

import br.com.segsense.application.catalog.CatalogAvailabilityQuery;
import br.com.segsense.application.catalog.CatalogAvailabilityQuery.CatalogHierarchy;
import br.com.segsense.domain.link.ContextLinkExpiredException;
import br.com.segsense.domain.link.ContextLinkNotFoundException;
import br.com.segsense.domain.link.ContextLinkRevokedException;
import br.com.segsense.domain.link.ContextLinkTemporarilyUnavailableException;
import br.com.segsense.domain.link.ContextLinkUnavailableException;
import br.com.segsense.domain.link.ContextLinkStatus;
import br.com.segsense.domain.link.OpaqueToken;
import br.com.segsense.domain.link.PublishedContextLink;
import br.com.segsense.domain.link.PublisherContextBinding;
import br.com.segsense.domain.opportunity.ContextFieldDefinition;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.OpportunityContent;
import br.com.segsense.domain.opportunity.OpportunityStatus;
import br.com.segsense.domain.opportunity.PublicationWindow;
import br.com.segsense.application.consent.ConsentNoticeRepository;
import br.com.segsense.application.opportunity.OpportunityRepository;
import br.com.segsense.domain.consent.ConsentNotice;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ResolvePublicContextLinkUseCase {

  public static final String APPLICATION_ID = "SEGSENSE";

  private final PublishedContextLinkRepository links;
  private final OpportunityRepository opportunities;
  private final CatalogAvailabilityQuery availability;
  private final ConsentNoticeRepository notices;
  private final Clock clock;

  public ResolvePublicContextLinkUseCase(
      PublishedContextLinkRepository links,
      OpportunityRepository opportunities,
      CatalogAvailabilityQuery availability,
      ConsentNoticeRepository notices,
      Clock clock) {
    this.links = links;
    this.opportunities = opportunities;
    this.availability = availability;
    this.notices = notices;
    this.clock = clock;
  }

  @Transactional(readOnly = true)
  public PublicContextEnvelope execute(String opaqueToken) {
    ResolvedPublicContext resolved = requireActive(opaqueToken);
    return envelope(resolved.opportunity(), resolved.link(), resolved.notice(), clock.instant());
  }

  public PublishedContextLink requireExisting(String opaqueToken) {
    if (!OpaqueToken.isWellFormed(opaqueToken)) {
      throw new ContextLinkNotFoundException();
    }
    return links.findByTokenDigest(OpaqueToken.digest(opaqueToken)).orElseThrow(ContextLinkNotFoundException::new);
  }

  public ResolvedPublicContext requireActive(String opaqueToken) {
    if (!OpaqueToken.isWellFormed(opaqueToken)) {
      throw new ContextLinkNotFoundException();
    }
    byte[] digest = OpaqueToken.digest(opaqueToken);
    PublishedContextLink link =
        links.findByTokenDigest(digest).orElseThrow(ContextLinkNotFoundException::new);
    Instant now = clock.instant();
    if (link.status() == ContextLinkStatus.REVOKED) {
      throw new ContextLinkRevokedException();
    }
    if (link.expiredAt(now)) {
      throw new ContextLinkExpiredException();
    }
    ContextualOpportunity opportunity =
        opportunities
            .findByScope(
                link.publisherId(), link.channelId(), link.environmentId(), link.opportunityId())
            .orElseThrow(ContextLinkUnavailableException::new);
    if (opportunity.status() == OpportunityStatus.REVOKED) {
      throw new ContextLinkUnavailableException();
    }
    if (opportunity.status() == OpportunityStatus.EXPIRED
        || PublicationWindow.isExpired(opportunity.current().content(), now)) {
      throw new ContextLinkExpiredException();
    }
    CatalogHierarchy hierarchy;
    try {
      hierarchy =
          availability.requireEnvironmentHierarchy(
              link.publisherId(), link.channelId(), link.environmentId());
    } catch (br.com.segsense.domain.catalog.ResourceNotFoundException exception) {
      throw new ContextLinkTemporarilyUnavailableException();
    }
    if (opportunity.status() == OpportunityStatus.PAUSED
        || !opportunity.effectivelyAvailable(
            hierarchy.publisher(), hierarchy.channel(), hierarchy.environment())
        || !PublicationWindow.isOpen(opportunity.current().content(), now)) {
      throw new ContextLinkTemporarilyUnavailableException();
    }
    if (opportunity.status() != OpportunityStatus.PUBLISHED) {
      throw new ContextLinkUnavailableException();
    }
    ConsentNotice notice =
        notices.findApprovedByOpportunityRevisionId(link.opportunityRevisionId()).orElse(null);
    return new ResolvedPublicContext(link, opportunity, notice);
  }

  private PublicContextEnvelope envelope(
      ContextualOpportunity opportunity,
      PublishedContextLink link,
      ConsentNotice notice,
      Instant now) {
    OpportunityContent content = opportunity.current().content();
    Map<String, Object> publisherValues = new LinkedHashMap<>();
    List<PublicPublisherBinding> publicBindings = new ArrayList<>();
    for (PublisherContextBinding binding : link.bindings()) {
      publisherValues.put(binding.fieldKey(), binding.publicValue());
      ContextFieldDefinition field =
          content.contextFields().stream()
              .filter(candidate -> candidate.key().equals(binding.fieldKey()))
              .findFirst()
              .orElse(null);
      publicBindings.add(
          new PublicPublisherBinding(
              binding.fieldKey(),
              field == null ? binding.fieldKey() : field.label(),
              binding.fieldType().name(),
              binding.publicValue()));
    }
    List<PublicUserField> userFields = new ArrayList<>();
    for (ContextFieldDefinition field : content.contextFields()) {
      boolean bound = publisherValues.containsKey(field.key());
      if (field.source() == ContextFieldSource.USER
          || (field.source() == ContextFieldSource.EITHER && !bound)) {
        userFields.add(
            new PublicUserField(
                field.key(),
                field.label(),
                field.type().name(),
                field.required(),
                field.allowedValues()));
      }
    }
    Instant validFrom = content.validFrom();
    Instant validUntil = content.validUntil();
    if (validUntil == null || link.expiresAt().isBefore(validUntil)) {
      validUntil = link.expiresAt();
    }
    Continuity continuity = Continuity.unavailable();
    if (notice != null && notice.effectivelyApproved()) {
      var snapshot = notice.approvedSnapshot();
      var contentNotice = snapshot.content();
      continuity =
          new Continuity(
              true,
              snapshot.versionNumber(),
              contentNotice.purposeTitle(),
              contentNotice.purposeDescription(),
              contentNotice.transparencyText(),
              contentNotice.noExternalSharingText());
    }
    return new PublicContextEnvelope(
        APPLICATION_ID,
        UUID.randomUUID(),
        content.title(),
        content.callToActionLabel(),
        content.contextMode().name(),
        new ContextSummary(content.contextSummaryTemplate(), Map.copyOf(publisherValues)),
        List.copyOf(publicBindings),
        List.copyOf(userFields),
        validFrom,
        validUntil,
        false,
        false,
        false,
        continuity);
  }

  public record PublicContextEnvelope(
      String applicationId,
      UUID resolutionId,
      String title,
      String callToActionLabel,
      String contextMode,
      ContextSummary contextSummary,
      List<PublicPublisherBinding> publisherBindings,
      List<PublicUserField> userFields,
      Instant effectiveValidFrom,
      Instant effectiveValidUntil,
      boolean quotationPerformed,
      boolean eligibilityEvaluated,
      boolean recommendationPerformed,
      Continuity continuity) {}

  public record Continuity(
      boolean available,
      Integer noticeVersion,
      String purposeTitle,
      String purposeDescription,
      String transparencyText,
      String noExternalSharingStatement) {

    public static Continuity unavailable() {
      return new Continuity(false, null, null, null, null, null);
    }
  }

  public record ResolvedPublicContext(
      PublishedContextLink link, ContextualOpportunity opportunity, ConsentNotice notice) {}

  public record ContextSummary(String template, Map<String, Object> publisherValues) {}

  public record PublicPublisherBinding(String fieldKey, String label, String type, Object value) {}

  public record PublicUserField(
      String key, String label, String type, boolean required, List<String> allowedValues) {}
}
