package br.com.segsense.inbound.http.link;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public record PublicContextLinkResponse(
    String applicationId,
    UUID resolutionId,
    String title,
    String callToActionLabel,
    String contextMode,
    ContextSummary contextSummary,
    List<PublisherBinding> publisherBindings,
    List<UserField> userFields,
    Instant effectiveValidFrom,
    Instant effectiveValidUntil,
    boolean quotationPerformed,
    boolean eligibilityEvaluated,
    boolean recommendationPerformed,
    Continuity continuity) {

  public record ContextSummary(String template, Map<String, Object> publisherValues) {}

  public record PublisherBinding(String fieldKey, String label, String type, Object value) {}

  public record UserField(
      String key, String label, String type, boolean required, List<String> allowedValues) {}

  public record Continuity(
      boolean available,
      Integer noticeVersion,
      String purposeTitle,
      String purposeDescription,
      String transparencyText,
      String noExternalSharingStatement) {}
}
