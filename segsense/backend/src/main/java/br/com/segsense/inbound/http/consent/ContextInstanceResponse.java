package br.com.segsense.inbound.http.consent;

import br.com.segsense.domain.consent.CollectedFieldValue;
import br.com.segsense.domain.consent.ConsentNoticeField;
import br.com.segsense.domain.consent.ContextInstance;
import com.fasterxml.jackson.annotation.JsonInclude;
import java.time.Instant;
import java.util.List;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record ContextInstanceResponse(
    String status,
    long expectedVersion,
    Instant expiresAt,
    int noticeVersion,
    boolean valuesUnavailable,
    boolean credentialIssued,
    String instanceCredential,
    boolean sessionEndsOnReload,
    List<CollectibleField> collectibleFields) {

  public static ContextInstanceResponse from(ContextInstance instance, String rawCredential) {
    return new ContextInstanceResponse(
        instance.status().name(),
        instance.version(),
        instance.expiresAt(),
        instance.noticeVersion(),
        instance.valuesUnavailable(),
        rawCredential != null,
        rawCredential,
        true,
        instance.collectibleFields().stream()
            .map(field -> CollectibleField.from(field, instance))
            .toList());
  }

  public record CollectibleField(
      String key,
      String label,
      String type,
      boolean required,
      List<String> allowedValues,
      Object value) {

    static CollectibleField from(ConsentNoticeField field, ContextInstance instance) {
      Object current =
          instance.visibleValues().stream()
              .filter(value -> value.fieldKey().equals(field.fieldKey()))
              .map(CollectedFieldValue::publicValue)
              .findFirst()
              .orElse(null);
      return new CollectibleField(
          field.fieldKey(),
          field.label(),
          field.fieldType().name(),
          field.required(),
          field.allowedValues(),
          current);
    }
  }
}
