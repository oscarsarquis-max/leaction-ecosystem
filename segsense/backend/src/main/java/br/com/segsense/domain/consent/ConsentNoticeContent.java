package br.com.segsense.domain.consent;

import br.com.segsense.domain.opportunity.OpportunityText;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;

public final class ConsentNoticeContent {

  private final String purposeTitle;
  private final String purposeDescription;
  private final String transparencyText;
  private final String noExternalSharingText;

  private ConsentNoticeContent(
      String purposeTitle,
      String purposeDescription,
      String transparencyText,
      String noExternalSharingText) {
    this.purposeTitle = purposeTitle;
    this.purposeDescription = purposeDescription;
    this.transparencyText = transparencyText;
    this.noExternalSharingText = noExternalSharingText;
  }

  public static ConsentNoticeContent parse(
      String purposeTitle,
      String purposeDescription,
      String transparencyText,
      String noExternalSharingText) {
    return new ConsentNoticeContent(
        OpportunityText.requiredLength(purposeTitle, "O título da finalidade", 5, 140),
        OpportunityText.requiredLength(purposeDescription, "A descrição da finalidade", 20, 2000),
        OpportunityText.requiredLength(transparencyText, "O texto de transparência", 20, 4000),
        OpportunityText.requiredLength(
            noExternalSharingText, "O texto de não compartilhamento", 10, 500));
  }

  public String purposeTitle() {
    return purposeTitle;
  }

  public String purposeDescription() {
    return purposeDescription;
  }

  public String transparencyText() {
    return transparencyText;
  }

  public String noExternalSharingText() {
    return noExternalSharingText;
  }

  public String contentHash(List<ConsentNoticeField> fields) {
    StringBuilder canonical = new StringBuilder();
    canonical
        .append(purposeTitle)
        .append('\n')
        .append(purposeDescription)
        .append('\n')
        .append(transparencyText)
        .append('\n')
        .append(noExternalSharingText);
    for (ConsentNoticeField field : fields) {
      canonical
          .append('\n')
          .append(field.fieldKey())
          .append(':')
          .append(field.fieldType().name())
          .append(':')
          .append(field.fieldSource().name())
          .append(':')
          .append(field.classification().name())
          .append(':')
          .append(field.required());
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

  @Override
  public boolean equals(Object other) {
    if (this == other) {
      return true;
    }
    if (!(other instanceof ConsentNoticeContent that)) {
      return false;
    }
    return Objects.equals(purposeTitle, that.purposeTitle)
        && Objects.equals(purposeDescription, that.purposeDescription)
        && Objects.equals(transparencyText, that.transparencyText)
        && Objects.equals(noExternalSharingText, that.noExternalSharingText);
  }

  @Override
  public int hashCode() {
    return Objects.hash(purposeTitle, purposeDescription, transparencyText, noExternalSharingText);
  }
}
