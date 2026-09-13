package br.com.segsense.domain.consent;

import br.com.segsense.domain.catalog.OptimisticConcurrencyException;
import br.com.segsense.domain.link.OpaqueToken;
import br.com.segsense.domain.link.PublishedContextLink;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

public final class ContextInstance {

  private final UUID id;
  private final UUID linkId;
  private final UUID publisherId;
  private final UUID channelId;
  private final UUID environmentId;
  private final UUID opportunityId;
  private final int revisionNumber;
  private final UUID opportunityRevisionId;
  private final UUID noticeId;
  private final int noticeVersion;
  private final UUID noticeSnapshotId;
  private final String noticeContentHash;
  private final byte[] credentialDigest;
  private final String credentialHint;
  private final byte[] idempotencyKeyDigest;
  private ContextInstanceStatus status;
  private boolean valuesUnavailable;
  private final Instant expiresAt;
  private final Instant createdAt;
  private Instant updatedAt;
  private final long version;
  private final UUID createdCorrelationId;
  private final List<CollectedFieldValue> values;
  private final List<ConsentNoticeField> collectibleFields;

  private ContextInstance(
      UUID id,
      UUID linkId,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      int revisionNumber,
      UUID opportunityRevisionId,
      UUID noticeId,
      int noticeVersion,
      UUID noticeSnapshotId,
      String noticeContentHash,
      byte[] credentialDigest,
      String credentialHint,
      byte[] idempotencyKeyDigest,
      ContextInstanceStatus status,
      boolean valuesUnavailable,
      Instant expiresAt,
      Instant createdAt,
      Instant updatedAt,
      long version,
      UUID createdCorrelationId,
      List<CollectedFieldValue> values,
      List<ConsentNoticeField> collectibleFields) {
    this.id = id;
    this.linkId = linkId;
    this.publisherId = publisherId;
    this.channelId = channelId;
    this.environmentId = environmentId;
    this.opportunityId = opportunityId;
    this.revisionNumber = revisionNumber;
    this.opportunityRevisionId = opportunityRevisionId;
    this.noticeId = noticeId;
    this.noticeVersion = noticeVersion;
    this.noticeSnapshotId = noticeSnapshotId;
    this.noticeContentHash = noticeContentHash;
    this.credentialDigest = credentialDigest;
    this.credentialHint = credentialHint;
    this.idempotencyKeyDigest = idempotencyKeyDigest;
    this.status = status;
    this.valuesUnavailable = valuesUnavailable;
    this.expiresAt = expiresAt;
    this.createdAt = createdAt;
    this.updatedAt = updatedAt;
    this.version = version;
    this.createdCorrelationId = createdCorrelationId;
    this.values = new ArrayList<>(values);
    this.collectibleFields = List.copyOf(collectibleFields);
  }

  public static ContextInstance create(
      UUID id,
      PublishedContextLink link,
      ContextualOpportunity opportunity,
      ConsentNotice notice,
      String rawCredential,
      byte[] idempotencyKeyDigest,
      Duration configuredTtl,
      Instant now,
      UUID correlationId) {
    notice.requireApprovedForNewInstance();
    if (!notice.opportunityRevisionId().equals(link.opportunityRevisionId())
        || notice.opportunityId() != null && !notice.opportunityId().equals(link.opportunityId())) {
      throw new ConsentNoticeObsoleteException();
    }
    ConsentNoticeSnapshot snapshot = notice.approvedSnapshot();
    Set<String> publisherBound =
        link.bindings().stream().map(binding -> binding.fieldKey()).collect(Collectors.toSet());
    List<ConsentNoticeField> collectible =
        snapshot.fields().stream()
            .filter(
                field ->
                    field.fieldSource() == ContextFieldSource.USER
                        || (field.fieldSource() == ContextFieldSource.EITHER
                            && !publisherBound.contains(field.fieldKey())))
            .toList();
    Instant expiresAt = expiry(link, opportunity, configuredTtl, now);
    ContextInstanceStatus initial =
        collectible.isEmpty()
            ? ContextInstanceStatus.AWAITING_DECISION
            : ContextInstanceStatus.AWAITING_INPUT;
    return new ContextInstance(
        Objects.requireNonNull(id, "id"),
        link.id(),
        link.publisherId(),
        link.channelId(),
        link.environmentId(),
        link.opportunityId(),
        link.revisionNumber(),
        link.opportunityRevisionId(),
        notice.id(),
        snapshot.versionNumber(),
        snapshot.id(),
        snapshot.contentHash(),
        OpaqueToken.digest(rawCredential),
        OpaqueToken.hint(rawCredential),
        idempotencyKeyDigest,
        initial,
        false,
        expiresAt,
        now,
        now,
        0L,
        correlationId,
        List.of(),
        collectible);
  }

  public static ContextInstance restore(
      UUID id,
      UUID linkId,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      int revisionNumber,
      UUID opportunityRevisionId,
      UUID noticeId,
      int noticeVersion,
      UUID noticeSnapshotId,
      String noticeContentHash,
      byte[] credentialDigest,
      String credentialHint,
      byte[] idempotencyKeyDigest,
      ContextInstanceStatus status,
      boolean valuesUnavailable,
      Instant expiresAt,
      Instant createdAt,
      Instant updatedAt,
      long version,
      UUID createdCorrelationId,
      List<CollectedFieldValue> values,
      List<ConsentNoticeField> collectibleFields) {
    return new ContextInstance(
        id,
        linkId,
        publisherId,
        channelId,
        environmentId,
        opportunityId,
        revisionNumber,
        opportunityRevisionId,
        noticeId,
        noticeVersion,
        noticeSnapshotId,
        noticeContentHash,
        OpaqueToken.requireDigest(credentialDigest),
        credentialHint,
        idempotencyKeyDigest,
        status,
        valuesUnavailable,
        expiresAt,
        createdAt,
        updatedAt,
        version,
        createdCorrelationId,
        values,
        collectibleFields);
  }

  public static boolean credentialMatches(byte[] storedDigest, String rawCredential) {
    if (!OpaqueToken.isWellFormed(rawCredential)) {
      return false;
    }
    return MessageDigest.isEqual(storedDigest, OpaqueToken.digest(rawCredential));
  }

  public void requireContinuityStillEffective(ConsentNotice notice) {
    if (notice == null
        || !notice.effectivelyApproved()
        || !notice.id().equals(noticeId)
        || notice.approvedVersion() == null
        || notice.approvedVersion() != noticeVersion) {
      throw new ConsentNoticeObsoleteException();
    }
  }

  public void replaceValues(List<CollectedFieldValue> incoming, long expectedVersion, Instant now) {
    requireExpected(expectedVersion);
    requireMutable(now);
    if (status != ContextInstanceStatus.AWAITING_INPUT
        && status != ContextInstanceStatus.AWAITING_DECISION) {
      throw new ContextInstanceUnauthorizedException();
    }
    Map<String, ConsentNoticeField> allowed = collectibleByKey();
    Map<String, CollectedFieldValue> next = new LinkedHashMap<>();
    for (CollectedFieldValue value : incoming) {
      ConsentNoticeField field = allowed.get(value.fieldKey());
      if (field == null) {
        throw new InvalidCollectedValueException();
      }
      if (next.containsKey(value.fieldKey())) {
        throw new InvalidCollectedValueException();
      }
      if (value.fieldType() != field.fieldType()
          || value.fieldSource() != field.fieldSource()) {
        throw new InvalidCollectedValueException();
      }
      next.put(value.fieldKey(), value);
    }
    values.clear();
    values.addAll(next.values());
    status =
        requiredSatisfied()
            ? ContextInstanceStatus.AWAITING_DECISION
            : ContextInstanceStatus.AWAITING_INPUT;
    updatedAt = now;
  }

  public ConsentDecision authorize(
      long expectedVersion, int acceptedNoticeVersion, boolean acknowledged, Instant now, UUID correlationId) {
    requireExpected(expectedVersion);
    requireMutable(now);
    if (!acknowledged) {
      throw new InvalidCollectedValueException();
    }
    if (acceptedNoticeVersion != noticeVersion) {
      throw new ConsentNoticeObsoleteException();
    }
    if (status != ContextInstanceStatus.AWAITING_DECISION || !requiredSatisfied()) {
      throw new ContextInstanceUnauthorizedException();
    }
    status = ContextInstanceStatus.AUTHORIZED;
    updatedAt = now;
    return ConsentDecision.record(
        UUID.randomUUID(),
        id,
        ConsentDecisionType.AUTHORIZED,
        noticeVersion,
        noticeContentHash,
        coveredFieldsHash(),
        now,
        correlationId,
        version,
        version + 1);
  }

  public ConsentDecision withdraw(long expectedVersion, Instant now, UUID correlationId) {
    if (expiredAt(now)) {
      throw new ContextInstanceExpiredException();
    }
    if (status == ContextInstanceStatus.AUTHORIZATION_WITHDRAWN) {
      return null;
    }
    requireExpected(expectedVersion);
    if (status != ContextInstanceStatus.AUTHORIZED) {
      throw new ContextInstanceUnauthorizedException();
    }
    status = ContextInstanceStatus.AUTHORIZATION_WITHDRAWN;
    valuesUnavailable = true;
    updatedAt = now;
    return ConsentDecision.record(
        UUID.randomUUID(),
        id,
        ConsentDecisionType.WITHDRAWN,
        noticeVersion,
        noticeContentHash,
        coveredFieldsHash(),
        now,
        correlationId,
        version,
        version + 1);
  }

  public List<CollectedFieldValue> visibleValues() {
    if (valuesUnavailable || status == ContextInstanceStatus.AUTHORIZATION_WITHDRAWN) {
      return List.of();
    }
    return List.copyOf(values);
  }

  public boolean expiredAt(Instant now) {
    return !now.isBefore(expiresAt);
  }

  private void requireMutable(Instant now) {
    if (expiredAt(now) || status == ContextInstanceStatus.EXPIRED) {
      throw new ContextInstanceExpiredException();
    }
    if (status == ContextInstanceStatus.AUTHORIZATION_WITHDRAWN) {
      throw new ContextInstanceUnauthorizedException();
    }
  }

  private void requireExpected(long expectedVersion) {
    if (expectedVersion != version) {
      throw new OptimisticConcurrencyException();
    }
  }

  private boolean requiredSatisfied() {
    Set<String> present = values.stream().map(CollectedFieldValue::fieldKey).collect(Collectors.toSet());
    for (ConsentNoticeField field : collectibleFields) {
      if (field.required() && !present.contains(field.fieldKey())) {
        return false;
      }
    }
    return true;
  }

  private Map<String, ConsentNoticeField> collectibleByKey() {
    Map<String, ConsentNoticeField> map = new LinkedHashMap<>();
    for (ConsentNoticeField field : collectibleFields) {
      map.put(field.fieldKey(), field);
    }
    return map;
  }

  private String coveredFieldsHash() {
    List<CollectedFieldValue> ordered = new ArrayList<>(values);
    ordered.sort(Comparator.comparing(CollectedFieldValue::fieldKey));
    StringBuilder canonical = new StringBuilder();
    for (CollectedFieldValue value : ordered) {
      canonical
          .append(value.fieldKey())
          .append('=')
          .append(value.canonicalText())
          .append('\n');
    }
    try {
      byte[] digest =
          MessageDigest.getInstance("SHA-256")
              .digest(canonical.toString().getBytes(StandardCharsets.UTF_8));
      return HexFormat.of().formatHex(digest);
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 required", exception);
    }
  }

  private static Instant expiry(
      PublishedContextLink link,
      ContextualOpportunity opportunity,
      Duration configuredTtl,
      Instant now) {
    Instant candidate = now.plus(configuredTtl);
    if (link.expiresAt().isBefore(candidate)) {
      candidate = link.expiresAt();
    }
    Instant opportunityUntil = opportunity.current().content().validUntil();
    if (opportunityUntil != null && opportunityUntil.isBefore(candidate)) {
      candidate = opportunityUntil;
    }
    if (!candidate.isAfter(now)) {
      throw new ContextInstanceExpiredException();
    }
    return candidate;
  }

  public UUID id() {
    return id;
  }

  public UUID linkId() {
    return linkId;
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

  public UUID noticeId() {
    return noticeId;
  }

  public int noticeVersion() {
    return noticeVersion;
  }

  public UUID noticeSnapshotId() {
    return noticeSnapshotId;
  }

  public String noticeContentHash() {
    return noticeContentHash;
  }

  public byte[] credentialDigest() {
    return credentialDigest;
  }

  public String credentialHint() {
    return credentialHint;
  }

  public byte[] idempotencyKeyDigest() {
    return idempotencyKeyDigest;
  }

  public ContextInstanceStatus status() {
    return status;
  }

  public boolean valuesUnavailable() {
    return valuesUnavailable;
  }

  public Instant expiresAt() {
    return expiresAt;
  }

  public Instant createdAt() {
    return createdAt;
  }

  public Instant updatedAt() {
    return updatedAt;
  }

  public long version() {
    return version;
  }

  public UUID createdCorrelationId() {
    return createdCorrelationId;
  }

  public List<CollectedFieldValue> values() {
    return List.copyOf(values);
  }

  public List<ConsentNoticeField> collectibleFields() {
    return collectibleFields;
  }
}
