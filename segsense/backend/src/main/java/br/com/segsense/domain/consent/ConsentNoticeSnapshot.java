package br.com.segsense.domain.consent;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

public final class ConsentNoticeSnapshot {

  private final UUID id;
  private final int versionNumber;
  private final ConsentNoticeContent content;
  private final String contentHash;
  private final Instant createdAt;
  private final String createdBy;
  private final List<ConsentNoticeField> fields;

  private ConsentNoticeSnapshot(
      UUID id,
      int versionNumber,
      ConsentNoticeContent content,
      String contentHash,
      Instant createdAt,
      String createdBy,
      List<ConsentNoticeField> fields) {
    this.id = id;
    this.versionNumber = versionNumber;
    this.content = content;
    this.contentHash = contentHash;
    this.createdAt = createdAt;
    this.createdBy = createdBy;
    this.fields = fields;
  }

  public static ConsentNoticeSnapshot create(
      UUID id,
      int versionNumber,
      ConsentNoticeContent content,
      Instant createdAt,
      String createdBy,
      List<ConsentNoticeField> fields) {
    List<ConsentNoticeField> ordered = ordered(fields);
    return new ConsentNoticeSnapshot(
        Objects.requireNonNull(id, "id"),
        versionNumber,
        Objects.requireNonNull(content, "content"),
        content.contentHash(ordered),
        Objects.requireNonNull(createdAt, "createdAt"),
        Objects.requireNonNull(createdBy, "createdBy"),
        ordered);
  }

  public static ConsentNoticeSnapshot restore(
      UUID id,
      int versionNumber,
      ConsentNoticeContent content,
      String contentHash,
      Instant createdAt,
      String createdBy,
      List<ConsentNoticeField> fields) {
    return new ConsentNoticeSnapshot(
        Objects.requireNonNull(id, "id"),
        versionNumber,
        Objects.requireNonNull(content, "content"),
        Objects.requireNonNull(contentHash, "contentHash"),
        Objects.requireNonNull(createdAt, "createdAt"),
        Objects.requireNonNull(createdBy, "createdBy"),
        ordered(fields));
  }

  private static List<ConsentNoticeField> ordered(List<ConsentNoticeField> fields) {
    List<ConsentNoticeField> copy = new ArrayList<>(fields == null ? List.of() : fields);
    copy.sort(Comparator.comparingInt(ConsentNoticeField::position));
    return List.copyOf(copy);
  }

  public UUID id() {
    return id;
  }

  public int versionNumber() {
    return versionNumber;
  }

  public ConsentNoticeContent content() {
    return content;
  }

  public String contentHash() {
    return contentHash;
  }

  public Instant createdAt() {
    return createdAt;
  }

  public String createdBy() {
    return createdBy;
  }

  public List<ConsentNoticeField> fields() {
    return fields;
  }
}
