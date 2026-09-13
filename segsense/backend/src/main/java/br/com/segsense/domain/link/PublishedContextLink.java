package br.com.segsense.domain.link;

import br.com.segsense.domain.catalog.OptimisticConcurrencyException;
import br.com.segsense.domain.catalog.InvalidStateTransitionException;
import br.com.segsense.domain.opportunity.AdministrativeJustification;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.OpportunityText;
import java.time.Instant;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

public final class PublishedContextLink {

  private final UUID id;
  private final UUID publisherId;
  private final UUID channelId;
  private final UUID environmentId;
  private final UUID opportunityId;
  private final int revisionNumber;
  private final UUID opportunityRevisionId;
  private final String placementKey;
  private final String label;
  private final byte[] tokenDigest;
  private final String tokenHint;
  private ContextLinkStatus status;
  private final Instant issuedAt;
  private final String issuedBy;
  private final Instant expiresAt;
  private Instant revokedAt;
  private String revokedBy;
  private String revocationReason;
  private final long version;
  private final UUID issuedCorrelationId;
  private UUID revokedCorrelationId;
  private final List<PublisherContextBinding> bindings;

  private PublishedContextLink(
      UUID id,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      int revisionNumber,
      UUID opportunityRevisionId,
      String placementKey,
      String label,
      byte[] tokenDigest,
      String tokenHint,
      ContextLinkStatus status,
      Instant issuedAt,
      String issuedBy,
      Instant expiresAt,
      Instant revokedAt,
      String revokedBy,
      String revocationReason,
      long version,
      UUID issuedCorrelationId,
      UUID revokedCorrelationId,
      List<PublisherContextBinding> bindings) {
    this.id = Objects.requireNonNull(id, "id");
    this.publisherId = Objects.requireNonNull(publisherId, "publisherId");
    this.channelId = Objects.requireNonNull(channelId, "channelId");
    this.environmentId = Objects.requireNonNull(environmentId, "environmentId");
    this.opportunityId = Objects.requireNonNull(opportunityId, "opportunityId");
    this.revisionNumber = revisionNumber;
    this.opportunityRevisionId = Objects.requireNonNull(opportunityRevisionId, "opportunityRevisionId");
    this.placementKey = Objects.requireNonNull(placementKey, "placementKey");
    this.label = Objects.requireNonNull(label, "label");
    this.tokenDigest = OpaqueToken.requireDigest(tokenDigest);
    this.tokenHint = Objects.requireNonNull(tokenHint, "tokenHint");
    this.status = Objects.requireNonNull(status, "status");
    this.issuedAt = Objects.requireNonNull(issuedAt, "issuedAt");
    this.issuedBy = Objects.requireNonNull(issuedBy, "issuedBy");
    this.expiresAt = Objects.requireNonNull(expiresAt, "expiresAt");
    this.revokedAt = revokedAt;
    this.revokedBy = revokedBy;
    this.revocationReason = revocationReason;
    this.version = version;
    this.issuedCorrelationId = Objects.requireNonNull(issuedCorrelationId, "issuedCorrelationId");
    this.revokedCorrelationId = revokedCorrelationId;
    this.bindings = List.copyOf(bindings);
  }

  public static IssuedLink issue(
      UUID id,
      ContextualOpportunity opportunity,
      String placementKey,
      String label,
      Instant expiresAt,
      Instant latestAllowedExpiry,
      Instant now,
      String actorSubject,
      UUID correlationId,
      String rawToken,
      List<PublisherBindingDraft> publisherContext) {
    Objects.requireNonNull(opportunity, "opportunity");
    Objects.requireNonNull(now, "now");
    Objects.requireNonNull(latestAllowedExpiry, "latestAllowedExpiry");
    if (opportunity.approvedRevision() == null
        || opportunity.approvedRevision() != opportunity.currentRevision()) {
      throw new ApprovedRevisionMismatchException();
    }
    Instant expiry = Objects.requireNonNull(expiresAt, "expiresAt");
    if (!expiry.isAfter(now) || expiry.isAfter(latestAllowedExpiry)) {
      throw new LinkExpiryInvalidException();
    }
    Instant revisionUntil = opportunity.current().content().validUntil();
    if (revisionUntil != null && expiry.isAfter(revisionUntil)) {
      throw new LinkExpiryInvalidException();
    }
    String parsedPlacement = PlacementKey.parse(placementKey);
    String parsedLabel = OpportunityText.requiredLength(label, "O rótulo do link", 5, 120);
    OpportunityText.rejectPersonalIdentifier(parsedLabel, "O rótulo do link");
    List<PublisherContextBinding> bindings =
        PublisherContextBindings.parse(opportunity.current().content(), publisherContext);
    byte[] digest = OpaqueToken.digest(rawToken);
    String hint = OpaqueToken.hint(rawToken);
    PublishedContextLink link =
        new PublishedContextLink(
            id,
            opportunity.publisherId(),
            opportunity.channelId(),
            opportunity.environmentId(),
            opportunity.id(),
            opportunity.currentRevision(),
            opportunity.current().id(),
            parsedPlacement,
            parsedLabel,
            digest,
            hint,
            ContextLinkStatus.ACTIVE,
            now,
            actorSubject,
            expiry,
            null,
            null,
            null,
            0L,
            correlationId,
            null,
            bindings);
    ContextLinkEvent event =
        new ContextLinkEvent(
            UUID.randomUUID(), id, ContextLinkEventType.ISSUED, now, actorSubject, correlationId);
    return new IssuedLink(link, event);
  }

  public static PublishedContextLink restore(
      UUID id,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      int revisionNumber,
      UUID opportunityRevisionId,
      String placementKey,
      String label,
      byte[] tokenDigest,
      String tokenHint,
      ContextLinkStatus status,
      Instant issuedAt,
      String issuedBy,
      Instant expiresAt,
      Instant revokedAt,
      String revokedBy,
      String revocationReason,
      long version,
      UUID issuedCorrelationId,
      UUID revokedCorrelationId,
      List<PublisherContextBinding> bindings) {
    return new PublishedContextLink(
        id,
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        revisionNumber,
        opportunityRevisionId,
        placementKey,
        label,
        tokenDigest,
        tokenHint,
        status,
        issuedAt,
        issuedBy,
        expiresAt,
        revokedAt,
        revokedBy,
        revocationReason,
        version,
        issuedCorrelationId,
        revokedCorrelationId,
        bindings == null ? List.of() : bindings);
  }

  public ContextLinkEvent revoke(
      long expectedVersion, String justification, Instant now, String actor, UUID correlationId) {
    requireExpectedVersion(expectedVersion);
    if (status != ContextLinkStatus.ACTIVE) {
      throw new InvalidStateTransitionException();
    }
    AdministrativeJustification text = AdministrativeJustification.required(justification);
    this.status = ContextLinkStatus.REVOKED;
    this.revokedAt = Objects.requireNonNull(now, "now");
    this.revokedBy = Objects.requireNonNull(actor, "actor");
    this.revocationReason = text.value();
    this.revokedCorrelationId = Objects.requireNonNull(correlationId, "correlationId");
    return new ContextLinkEvent(
        UUID.randomUUID(), id, ContextLinkEventType.REVOKED, now, actor, correlationId);
  }

  public void requireExpectedVersion(long expectedVersion) {
    if (this.version != expectedVersion) {
      throw new OptimisticConcurrencyException();
    }
  }

  public boolean expiredAt(Instant now) {
    return !now.isBefore(expiresAt);
  }

  public EffectiveLinkStatus effectiveStatus(Instant now) {
    if (status == ContextLinkStatus.REVOKED) {
      return EffectiveLinkStatus.REVOKED;
    }
    if (expiredAt(now)) {
      return EffectiveLinkStatus.EXPIRED;
    }
    return EffectiveLinkStatus.ACTIVE;
  }

  public UUID id() {
    return id;
  }

  public UUID publisherId() {
    return publisherId;
  }

  public UUID channelId() {
    return channelId;
  }

  public UUID environmentId() {
    return environmentId;
  }

  public UUID opportunityId() {
    return opportunityId;
  }

  public int revisionNumber() {
    return revisionNumber;
  }

  public UUID opportunityRevisionId() {
    return opportunityRevisionId;
  }

  public String placementKey() {
    return placementKey;
  }

  public String label() {
    return label;
  }

  public byte[] tokenDigest() {
    return OpaqueToken.requireDigest(tokenDigest);
  }

  public String tokenHint() {
    return tokenHint;
  }

  public ContextLinkStatus status() {
    return status;
  }

  public Instant issuedAt() {
    return issuedAt;
  }

  public String issuedBy() {
    return issuedBy;
  }

  public Instant expiresAt() {
    return expiresAt;
  }

  public Instant revokedAt() {
    return revokedAt;
  }

  public String revokedBy() {
    return revokedBy;
  }

  public String revocationReason() {
    return revocationReason;
  }

  public long version() {
    return version;
  }

  public UUID issuedCorrelationId() {
    return issuedCorrelationId;
  }

  public UUID revokedCorrelationId() {
    return revokedCorrelationId;
  }

  public List<PublisherContextBinding> bindings() {
    return bindings;
  }

  public record IssuedLink(PublishedContextLink link, ContextLinkEvent event) {}
}
