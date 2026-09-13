package br.com.segsense.domain.link;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.segsense.domain.opportunity.ContextFieldDefinition;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.ContextMode;
import br.com.segsense.domain.opportunity.FieldClassification;
import br.com.segsense.domain.opportunity.OpportunityContent;
import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.Test;

class OpaqueTokenAndBindingTest {

  @Test
  void digestIsSha256OfWellFormedToken() {
    String token = "A".repeat(43);
    assertThat(OpaqueToken.isWellFormed(token)).isTrue();
    assertThat(OpaqueToken.digest(token)).hasSize(32);
    assertThat(OpaqueToken.hint(token)).isEqualTo("AAAAAAAA");
    assertThatThrownBy(() -> OpaqueToken.digest("short")).isInstanceOf(IllegalArgumentException.class);
    assertThat(OpaqueToken.isWellFormed("not a token")).isFalse();
  }

  @Test
  void bindingsAcceptTypedPublisherValuesAndRejectCoercion() {
    OpportunityContent content = dynamicContent();
    List<PublisherContextBinding> bindings =
        PublisherContextBindings.parse(
            content,
            List.of(
                new PublisherBindingDraft("riskType", "quebra-safra"),
                new PublisherBindingDraft("area", new BigDecimal("12.50")),
                new PublisherBindingDraft("insured", Boolean.TRUE),
                new PublisherBindingDraft("seasonStart", "2026-09-01")));
    assertThat(bindings).hasSize(4);
    assertThat(bindings)
        .extracting(PublisherContextBinding::fieldSource)
        .containsOnly(ContextFieldSource.PUBLISHER, ContextFieldSource.EITHER);

    assertThatThrownBy(
            () ->
                PublisherContextBindings.parse(
                    content, List.of(new PublisherBindingDraft("area", "12.5"))))
        .isInstanceOf(InvalidPublisherContextException.class);
    assertThatThrownBy(
            () ->
                PublisherContextBindings.parse(
                    content, List.of(new PublisherBindingDraft("insured", "true"))))
        .isInstanceOf(InvalidPublisherContextException.class);
    assertThatThrownBy(
            () ->
                PublisherContextBindings.parse(
                    content, List.of(new PublisherBindingDraft("unknown", "x"))))
        .isInstanceOf(InvalidPublisherContextException.class);
    assertThatThrownBy(
            () ->
                PublisherContextBindings.parse(
                    content,
                    List.of(
                        new PublisherBindingDraft("riskType", "quebra-safra"),
                        new PublisherBindingDraft("riskType", "seca"))))
        .isInstanceOf(InvalidPublisherContextException.class);
    assertThatThrownBy(
            () ->
                PublisherContextBindings.parse(
                    content, List.of(new PublisherBindingDraft("comment", "texto do usuario"))))
        .isInstanceOf(InvalidPublisherContextException.class);
    assertThatThrownBy(
            () ->
                PublisherContextBindings.parse(
                    content, List.of(new PublisherBindingDraft("riskType", "{\"a\":1}"))))
        .isInstanceOf(InvalidPublisherContextException.class);
    assertThatThrownBy(
            () ->
                PublisherContextBindings.parse(
                    content, List.of(new PublisherBindingDraft("cropNote", "<script>x</script>"))))
        .isInstanceOf(InvalidPublisherContextException.class);
    assertThatThrownBy(
            () ->
                PublisherContextBindings.parse(
                    content, List.of(new PublisherBindingDraft("cropNote", "cpf do produtor"))))
        .isInstanceOf(InvalidPublisherContextException.class);
  }

  @Test
  void requiredPublisherFieldMustBeBoundAndStaticRejectsBindings() {
    OpportunityContent dynamic = dynamicContent();
    assertThatThrownBy(() -> PublisherContextBindings.parse(dynamic, List.of()))
        .isInstanceOf(RequiredPublisherContextMissingException.class);

    OpportunityContent stat =
        OpportunityContent.parse(
            "Titulo estatico ok",
            ContextMode.STATIC,
            "Resumo estatico de contexto.",
            "Objetivo estatico de avaliacao.",
            "Avaliar",
            null,
            null,
            List.of());
    assertThat(PublisherContextBindings.parse(stat, List.of())).isEmpty();
    assertThatThrownBy(
            () ->
                PublisherContextBindings.parse(
                    stat, List.of(new PublisherBindingDraft("riskType", "quebra-safra"))))
        .isInstanceOf(InvalidPublisherContextException.class);
  }

  private static OpportunityContent dynamicContent() {
    return OpportunityContent.parse(
        "Protecao agricola xx",
        ContextMode.DYNAMIC,
        "Resumo para {{riskType}} no ambiente.",
        "Quero avaliar protecao neste contexto.",
        "Avaliar",
        null,
        null,
        List.of(
            field("riskType", "Tipo de risco", ContextFieldType.ENUM, true, ContextFieldSource.PUBLISHER, List.of("quebra-safra", "seca"), 0),
            field("area", "Area", ContextFieldType.NUMBER, true, ContextFieldSource.PUBLISHER, List.of(), 1),
            field("insured", "Segurado", ContextFieldType.BOOLEAN, false, ContextFieldSource.EITHER, List.of(), 2),
            field("seasonStart", "Inicio", ContextFieldType.DATE, false, ContextFieldSource.EITHER, List.of(), 3),
            field("cropNote", "Nota", ContextFieldType.TEXT, false, ContextFieldSource.PUBLISHER, List.of(), 4),
            field("comment", "Comentario", ContextFieldType.TEXT, false, ContextFieldSource.USER, List.of(), 5)));
  }

  private static ContextFieldDefinition field(
      String key,
      String label,
      ContextFieldType type,
      boolean required,
      ContextFieldSource source,
      List<String> allowed,
      int position) {
    return ContextFieldDefinition.parse(
        key,
        label,
        type,
        required,
        source,
        FieldClassification.NON_PERSONAL,
        allowed,
        position);
  }
}
