package br.com.segsense.domain.consent;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.segsense.domain.opportunity.ContextFieldDefinition;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.FieldClassification;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ConsentNoticeDomainTest {

  @Test
  void hashesContentAndRejectsPersonalOrPublisherOnlyFields() {
    ConsentNoticeContent content =
        ConsentNoticeContent.parse(
            "Uso no SegSense",
            "Continuar esta jornada apenas no SegSense, sem envio externo.",
            "As informacoes desta etapa permanecem no SegSense e nao vao a seguradora.",
            "Nao ha compartilhamento externo nesta etapa.");
    ConsentNoticeField field =
        ConsentNoticeField.fromDefinition(
            UUID.randomUUID(),
            UUID.randomUUID(),
            ContextFieldDefinition.parse(
                "comment",
                "Comentario",
                ContextFieldType.TEXT,
                false,
                ContextFieldSource.USER,
                FieldClassification.NON_PERSONAL,
                List.of(),
                0));
    assertThat(content.contentHash(List.of(field))).hasSize(64);

    assertThatThrownBy(
            () ->
                ConsentNoticeField.fromDefinition(
                    UUID.randomUUID(),
                    UUID.randomUUID(),
                    ContextFieldDefinition.parse(
                        "riskType",
                        "Tipo de risco",
                        ContextFieldType.TEXT,
                        true,
                        ContextFieldSource.PUBLISHER,
                        FieldClassification.NON_PERSONAL,
                        List.of(),
                        0)))
        .isInstanceOf(br.com.segsense.domain.catalog.CatalogValidationException.class);
  }

  @Test
  void collectedValuesRejectCoercionAndUnknownShapes() {
    ConsentNoticeField field =
        ConsentNoticeField.fromDefinition(
            UUID.randomUUID(),
            UUID.randomUUID(),
            ContextFieldDefinition.parse(
                "areaSize",
                "Area",
                ContextFieldType.NUMBER,
                true,
                ContextFieldSource.USER,
                FieldClassification.NON_PERSONAL,
                List.of(),
                0));
    CollectedFieldValue number = CollectedFieldValue.parse(UUID.randomUUID(), field, 12.5);
    assertThat(number.publicValue()).isEqualTo(new java.math.BigDecimal("12.5"));
    assertThatThrownBy(() -> CollectedFieldValue.parse(UUID.randomUUID(), field, "12.5"))
        .isInstanceOf(InvalidCollectedValueException.class);
    assertThatThrownBy(() -> CollectedFieldValue.parse(UUID.randomUUID(), field, Map.of("a", 1)))
        .isInstanceOf(InvalidCollectedValueException.class);
    assertThatThrownBy(() -> CollectedFieldValue.parse(UUID.randomUUID(), field, List.of(1)))
        .isInstanceOf(InvalidCollectedValueException.class);
  }

  @Test
  void idempotencyKeyRejectsMissingWeakOrShortValues() {
    assertThatThrownBy(() -> IdempotencyKey.required(null))
        .isInstanceOf(IdempotencyKeyRequiredException.class);
    assertThatThrownBy(() -> IdempotencyKey.required(" "))
        .isInstanceOf(IdempotencyKeyRequiredException.class);
    assertThatThrownBy(() -> IdempotencyKey.required("short"))
        .isInstanceOf(InvalidIdempotencyKeyException.class);
    assertThatThrownBy(() -> IdempotencyKey.required("aaaaaaaaaaaaaaaa"))
        .isInstanceOf(InvalidIdempotencyKeyException.class);
    assertThat(IdempotencyKey.required("idempotency-key-01")).isEqualTo("idempotency-key-01");
  }
}
