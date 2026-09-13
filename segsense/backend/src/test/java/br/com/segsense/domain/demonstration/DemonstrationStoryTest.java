package br.com.segsense.domain.demonstration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.catalog.InvalidStateTransitionException;
import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.opportunity.AdministrativeJustification;
import br.com.segsense.domain.opportunity.SegregationOfDutiesException;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class DemonstrationStoryTest {

  private static final Instant NOW = Instant.parse("2026-09-12T12:00:00Z");
  private static final UUID SOURCE_ID = UUID.fromString("11111111-1111-4111-8111-000000000001");

  @Test
  void rejectsUnsafeAndPersonalContent() {
    assertThatThrownBy(() -> draft("<script>x</script>", "texto seguro de demonstracao sem dado pessoal."))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> draft("Titulo valido", "Informe o CPF do cliente neste texto."))
        .isInstanceOf(CatalogValidationException.class);
  }

  @Test
  void submitterCannotApprove() {
    DemonstrationStory story = create();
    story.submit(justification(), NOW, "writer");
    assertThatThrownBy(() -> story.approve(justification(), NOW, "writer"))
        .isInstanceOf(SegregationOfDutiesException.class);
    story.approve(justification(), NOW, "approver");
    assertThat(story.workflowStatus()).isEqualTo(DemonstrationWorkflowStatus.APPROVED);
  }

  @Test
  void cannotPublishFromDraft() {
    DemonstrationStory story = create();
    assertThatThrownBy(() -> story.publish(justification(), NOW, "publisher"))
        .isInstanceOf(InvalidStateTransitionException.class);
    assertThat(story.publiclyVisible()).isFalse();
  }

  private static DemonstrationStory create() {
    return DemonstrationStory.create(
        UUID.randomUUID(),
        ResourceKey.parse("icatu-demonstracao"),
        content("Titulo valido", "texto seguro de demonstracao sem dado pessoal."),
        sources(),
        NOW,
        "writer");
  }

  private static DemonstrationStory.DemonstrationRevisionContent draft(String title, String summary) {
    return content(title, summary);
  }

  private static DemonstrationStory.DemonstrationRevisionContent content(String title, String summary) {
    return new DemonstrationStory.DemonstrationRevisionContent(
        title,
        summary,
        "Gestor comercial",
        "Cenario demonstrativo nao oficial, sem oferta de seguro.",
        List.of(new DemonstrationBlock(UUID.randomUUID(), 1, "Origem", "Artigo ilustrativo generico de risco agricola.")),
        List.of(
            new DemonstrationClaim(
                UUID.randomUUID(),
                1,
                "O Hub publico informa que as APIs da Icatu sao autenticadas.",
                SOURCE_ID)));
  }

  private static Map<UUID, DemonstrationSource> sources() {
    return Map.of(
        SOURCE_ID,
        new DemonstrationSource(
            SOURCE_ID,
            "icatu-hub-home",
            "https://portal-api.icatuseguros.com.br/",
            LocalDate.parse("2026-09-12"),
            "PUBLIC",
            "VERIFIED",
            "Pagina publica do Hub."));
  }

  private static AdministrativeJustification justification() {
    return AdministrativeJustification.required("Justificativa editorial com dez chars.");
  }
}
