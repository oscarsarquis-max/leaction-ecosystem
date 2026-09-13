package br.com.segsense.domain.opportunity;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ChannelType;
import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.DisplayName;
import br.com.segsense.domain.catalog.EnvironmentType;
import br.com.segsense.domain.catalog.LifecycleStatus;
import br.com.segsense.domain.catalog.OptimisticConcurrencyException;
import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceKey;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class OpportunityAggregateTest {

  private static final Instant NOW = Instant.parse("2026-09-04T12:00:00Z");
  private static final String ACTOR = "opportunity-tester";

  @Test
  void createStartsDraftRevisionOneWhenParentsAreAvailable() {
    Hierarchy hierarchy = activeHierarchy();
    ContextualOpportunity opportunity =
        ContextualOpportunity.create(
            UUID.randomUUID(),
            hierarchy.publisher,
            hierarchy.channel,
            hierarchy.environment,
            ResourceKey.parse("crop-risk"),
            staticContent("Avaliar proteção agrícola"),
            NOW,
            ACTOR);

    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.DRAFT);
    assertThat(opportunity.currentRevision()).isEqualTo(1);
    assertThat(opportunity.current().revisionNumber()).isEqualTo(1);
    assertThat(opportunity.key().value()).isEqualTo("crop-risk");
    assertThat(
            opportunity.effectivelyAvailable(
                hierarchy.publisher, hierarchy.channel, hierarchy.environment))
        .isTrue();
  }

  @Test
  void createRejectedWhenParentsAreNotEffectivelyAvailable() {
    Publisher publisher =
        Publisher.create(
            UUID.randomUUID(), ResourceKey.parse("acme"), DisplayName.parse("Acme"), NOW, ACTOR);
    Channel channel =
        Channel.create(
            UUID.randomUUID(),
            publisher,
            ResourceKey.parse("portal"),
            DisplayName.parse("Portal"),
            ChannelType.WEBSITE,
            NOW,
            ACTOR);
    ContextualEnvironment environment =
        ContextualEnvironment.create(
            UUID.randomUUID(),
            publisher,
            channel,
            ResourceKey.parse("home"),
            DisplayName.parse("Home"),
            EnvironmentType.PAGE,
            null,
            NOW,
            ACTOR);
    assertThatThrownBy(
            () ->
                ContextualOpportunity.create(
                    UUID.randomUUID(),
                    publisher,
                    channel,
                    environment,
                    ResourceKey.parse("crop-risk"),
                    staticContent("Avaliar proteção agrícola"),
                    NOW,
                    ACTOR))
        .isInstanceOf(InvalidParentStateException.class);
  }

  @Test
  void createRejectedOnCrossHierarchy() {
    Hierarchy one = activeHierarchy();
    Hierarchy other = activeHierarchy();
    assertThatThrownBy(
            () ->
                ContextualOpportunity.create(
                    UUID.randomUUID(),
                    one.publisher,
                    other.channel,
                    one.environment,
                    ResourceKey.parse("crop-risk"),
                    staticContent("Avaliar proteção agrícola"),
                    NOW,
                    ACTOR))
        .isInstanceOf(ResourceNotFoundException.class);
  }

  @Test
  void reviseCreatesImmutableNextRevisionAndRejectsStaleBaseAndSameContent() {
    Hierarchy hierarchy = activeHierarchy();
    ContextualOpportunity opportunity =
        ContextualOpportunity.create(
            UUID.randomUUID(),
            hierarchy.publisher,
            hierarchy.channel,
            hierarchy.environment,
            ResourceKey.parse("crop-risk"),
            staticContent("Avaliar proteção agrícola"),
            NOW,
            ACTOR);
    OpportunityRevision first = opportunity.current();
    OpportunityContent next = staticContent("Avaliar outra proteção agric");
    OpportunityRevision second = opportunity.revise(0L, 1, next, NOW.plusSeconds(1), ACTOR);

    assertThat(second.revisionNumber()).isEqualTo(2);
    assertThat(opportunity.currentRevision()).isEqualTo(2);
    assertThat(first.content().title()).isEqualTo("Avaliar proteção agrícola");
    assertThat(opportunity.current().content().title()).isEqualTo("Avaliar outra proteção agric");

    ContextualOpportunity concurrent =
        ContextualOpportunity.restore(
            opportunity.id(),
            opportunity.publisherId(),
            opportunity.channelId(),
            opportunity.environmentId(),
            opportunity.key(),
            opportunity.status(),
            2,
            1L,
            opportunity.createdAt(),
            opportunity.updatedAt(),
            opportunity.createdBy(),
            opportunity.updatedBy(),
            second,
            null,
            null,
            null,
            null,
            null);
    assertThatThrownBy(
            () -> concurrent.revise(0L, 2, staticContent("Terceira revisão xx"), NOW, ACTOR))
        .isInstanceOf(OptimisticConcurrencyException.class);
    assertThatThrownBy(
            () -> concurrent.revise(1L, 1, staticContent("Terceira revisão xx"), NOW, ACTOR))
        .isInstanceOf(StaleOpportunityRevisionException.class);
    assertThatThrownBy(() -> concurrent.revise(1L, 2, next, NOW, ACTOR))
        .isInstanceOf(NoContentChangeException.class);
  }

  @Test
  void parentSuspendDoesNotChangeDraftStatusButClearsAvailability() {
    Hierarchy hierarchy = activeHierarchy();
    ContextualOpportunity opportunity =
        ContextualOpportunity.create(
            UUID.randomUUID(),
            hierarchy.publisher,
            hierarchy.channel,
            hierarchy.environment,
            ResourceKey.parse("crop-risk"),
            staticContent("Avaliar proteção agrícola"),
            NOW,
            ACTOR);
    hierarchy.environment.transitionTo(
        LifecycleStatus.SUSPENDED, hierarchy.publisher, hierarchy.channel, NOW.plusSeconds(2), ACTOR);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.DRAFT);
    assertThat(
            opportunity.effectivelyAvailable(
                hierarchy.publisher, hierarchy.channel, hierarchy.environment))
        .isFalse();
  }

  @Test
  void staticDynamicHybridAndPlaceholderRules() {
    assertThat(staticContent("Conteúdo estático válido").contextFields()).isEmpty();
    assertThatThrownBy(
            () ->
                OpportunityContent.parse(
                    "Título válido aqui",
                    ContextMode.STATIC,
                    "Resumo estático de contexto.",
                    "Objetivo estático de avaliação.",
                    "Avaliar",
                    null,
                    null,
                    List.of(enumField("cropType", "Tipo de cultura", 0))))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(
            () ->
                OpportunityContent.parse(
                    "Título válido aqui",
                    ContextMode.DYNAMIC,
                    "Resumo dinâmico de contexto.",
                    "Objetivo dinâmico de avaliação.",
                    "Avaliar",
                    null,
                    null,
                    List.of()))
        .isInstanceOf(CatalogValidationException.class);

    OpportunityContent hybrid =
        OpportunityContent.parse(
            "Proteção para {{cropType}}",
            ContextMode.HYBRID,
            "Resumo para {{cropType}} e {{riskType}}.",
            "Quero avaliar proteção para {{cropType}} diante do risco de {{riskType}}.",
            "Avaliar",
            null,
            null,
            List.of(
                enumField("cropType", "Tipo de cultura", 0),
                enumField("riskType", "Tipo de risco", 1)));
    assertThat(hybrid.contextMode()).isEqualTo(ContextMode.HYBRID);
    assertThat(hybrid.contextFields()).hasSize(2);

    assertThatThrownBy(
            () ->
                OpportunityContent.parse(
                    "Título válido aqui",
                    ContextMode.DYNAMIC,
                    "Resumo para {{unknownField}} no texto.",
                    "Objetivo dinâmico de avaliação.",
                    "Avaliar",
                    null,
                    null,
                    List.of(enumField("cropType", "Tipo de cultura", 0))))
        .isInstanceOf(CatalogValidationException.class);

    assertThatThrownBy(
            () ->
                OpportunityContent.parse(
                    "Título válido aqui",
                    ContextMode.DYNAMIC,
                    "Resumo dinâmico de contexto.",
                    "Objetivo dinâmico de avaliação.",
                    "Avaliar",
                    null,
                    null,
                    List.of(
                        enumField("cropType", "Tipo de cultura", 0),
                        enumField("cropType", "Outra cultura", 1))))
        .isInstanceOf(CatalogValidationException.class);
  }

  @Test
  void rejectsPersonalUnsafeTemporalAndArbitraryFieldPayloads() {
    assertThatThrownBy(() -> ContextFieldDefinition.parse("cpf", "Documento", ContextFieldType.TEXT, false, ContextFieldSource.USER, FieldClassification.NON_PERSONAL, null, 0))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(
            () ->
                ContextFieldDefinition.parse(
                    "cropType",
                    "Nome do segurado",
                    ContextFieldType.TEXT,
                    false,
                    ContextFieldSource.USER,
                    FieldClassification.NON_PERSONAL,
                    null,
                    0))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(
            () ->
                OpportunityContent.parse(
                    "<script>x</script>",
                    ContextMode.STATIC,
                    "Resumo estático de contexto.",
                    "Objetivo estático de avaliação.",
                    "Avaliar",
                    null,
                    null,
                    List.of()))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(
            () ->
                OpportunityContent.parse(
                    "Título válido aqui",
                    ContextMode.STATIC,
                    "Resumo estático de contexto.",
                    "Objetivo estático de avaliação.",
                    "Avaliar",
                    Instant.parse("2026-09-10T00:00:00Z"),
                    Instant.parse("2026-09-01T00:00:00Z"),
                    List.of()))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(
            () ->
                ContextFieldDefinition.parse(
                    "cropType",
                    "Tipo de cultura",
                    ContextFieldType.TEXT,
                    false,
                    ContextFieldSource.PUBLISHER,
                    FieldClassification.NON_PERSONAL,
                    List.of("soja"),
                    0))
        .isInstanceOf(CatalogValidationException.class);
  }

  private static OpportunityContent staticContent(String title) {
    return OpportunityContent.parse(
        title,
        ContextMode.STATIC,
        "Resumo estático de contexto.",
        "Objetivo estático de avaliação.",
        "Avaliar",
        null,
        null,
        List.of());
  }

  private static ContextFieldDefinition enumField(String key, String label, int position) {
    return ContextFieldDefinition.parse(
        key,
        label,
        ContextFieldType.ENUM,
        true,
        ContextFieldSource.PUBLISHER,
        FieldClassification.NON_PERSONAL,
        List.of("soja", "milho"),
        position);
  }

  private static Hierarchy activeHierarchy() {
    Publisher publisher =
        Publisher.create(
            UUID.randomUUID(), ResourceKey.parse("acme-" + UUID.randomUUID().toString().substring(0, 8)), DisplayName.parse("Acme"), NOW, ACTOR);
    publisher.transitionTo(LifecycleStatus.ACTIVE, NOW.plusSeconds(1), ACTOR);
    Channel channel =
        Channel.create(
            UUID.randomUUID(),
            publisher,
            ResourceKey.parse("portal"),
            DisplayName.parse("Portal"),
            ChannelType.WEBSITE,
            NOW,
            ACTOR);
    channel.transitionTo(LifecycleStatus.ACTIVE, publisher, NOW.plusSeconds(1), ACTOR);
    ContextualEnvironment environment =
        ContextualEnvironment.create(
            UUID.randomUUID(),
            publisher,
            channel,
            ResourceKey.parse("home"),
            DisplayName.parse("Home"),
            EnvironmentType.PAGE,
            null,
            NOW,
            ACTOR);
    environment.transitionTo(
        LifecycleStatus.ACTIVE, publisher, channel, NOW.plusSeconds(1), ACTOR);
    return new Hierarchy(publisher, channel, environment);
  }

  private record Hierarchy(Publisher publisher, Channel channel, ContextualEnvironment environment) {}
}
