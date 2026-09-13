package br.com.segsense.inbound.http.consent;

import br.com.segsense.domain.consent.ConsentNotice;
import br.com.segsense.domain.consent.ConsentNoticeField;
import br.com.segsense.domain.consent.ConsentNoticeSnapshot;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record ConsentNoticeResponse(
    UUID id,
    UUID opportunityId,
    int revisionNumber,
    int currentVersion,
    Integer approvedVersion,
    String status,
    long version,
    Instant createdAt,
    Instant updatedAt,
    Snapshot current,
    List<Snapshot> versions) {

  public static ConsentNoticeResponse from(ConsentNotice notice) {
    ConsentNoticeSnapshot currentSnapshot = notice.currentSnapshot();
    return new ConsentNoticeResponse(
        notice.id(),
        notice.opportunityId(),
        notice.revisionNumber(),
        notice.currentVersion(),
        notice.approvedVersion(),
        notice.status().name(),
        notice.version(),
        notice.createdAt(),
        notice.updatedAt(),
        Snapshot.from(currentSnapshot),
        notice.snapshots().stream().map(Snapshot::from).toList());
  }

  public record Snapshot(
      int versionNumber,
      String purposeTitle,
      String purposeDescription,
      String transparencyText,
      String noExternalSharingText,
      Instant createdAt,
      List<CoveredField> fields) {

    static Snapshot from(ConsentNoticeSnapshot snapshot) {
      return new Snapshot(
          snapshot.versionNumber(),
          snapshot.content().purposeTitle(),
          snapshot.content().purposeDescription(),
          snapshot.content().transparencyText(),
          snapshot.content().noExternalSharingText(),
          snapshot.createdAt(),
          snapshot.fields().stream().map(CoveredField::from).toList());
    }
  }

  public record CoveredField(
      String key, String label, String type, String source, boolean required, List<String> allowedValues) {

    static CoveredField from(ConsentNoticeField field) {
      return new CoveredField(
          field.fieldKey(),
          field.label(),
          field.fieldType().name(),
          field.fieldSource().name(),
          field.required(),
          field.allowedValues());
    }
  }
}
