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
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class OpportunityGovernanceTest {

  private static final Instant NOW = Instant.parse("2026-09-04T12:00:00Z");
  private static final String AUTHOR = "author";
  private static final String REVIEWER = "reviewer";
  private static final String ACTIVATOR = "activator";
  private static final UUID CORRELATION = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");

  @Test
  void validLifecycleAndInvalidTransitions() {
    Hierarchy hierarchy = activeHierarchy();
    ContextualOpportunity opportunity = draft(hierarchy);

    assertThatThrownBy(
            () -> opportunity.approve(0L, 1, NOW, REVIEWER, CORRELATION))
        .isInstanceOf(InvalidGovernanceTransitionException.class);
    assertThatThrownBy(
            () ->
                opportunity.activatePublication(
                    0L,
                    NOW,
                    ACTIVATOR,
                    CORRELATION,
                    hierarchy.publisher,
                    hierarchy.channel,
                    hierarchy.environment))
        .isInstanceOf(InvalidGovernanceTransitionException.class);

    GovernanceEffect submitted = opportunity.submit(0L, NOW, AUTHOR, CORRELATION);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.UNDER_REVIEW);
    assertThat(opportunity.submittedRevision()).isEqualTo(1);
    assertThat(submitted.submission().revisionNumber()).isEqualTo(1);
    assertThat(submitted.event().correlationId()).isEqualTo(CORRELATION);
    assertThatThrownBy(
            () -> opportunity.revise(0L, 1, staticContent("Nova revisão válida xx"), NOW, AUTHOR))
        .isInstanceOf(InvalidGovernanceTransitionException.class);
    assertThatThrownBy(() -> opportunity.submit(0L, NOW, AUTHOR, CORRELATION))
        .isInstanceOf(InvalidGovernanceTransitionException.class);

    assertThatThrownBy(
            () ->
                opportunity.returnForChanges(
                    0L, 1, "Ajustar o resumo editorial.", NOW, AUTHOR, CORRELATION))
        .isInstanceOf(SegregationOfDutiesException.class);

    opportunity.returnForChanges(
        0L, 1, "Ajustar o resumo editorial.", NOW, REVIEWER, CORRELATION);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.DRAFT);
    assertThat(opportunity.openSubmissionId()).isNull();

    opportunity.revise(0L, 1, staticContent("Revisão devolvida ajustada"), NOW, AUTHOR);
    opportunity.submit(0L, NOW, AUTHOR, CORRELATION);
    opportunity.approve(0L, 2, NOW, REVIEWER, CORRELATION);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.APPROVED);
    assertThat(opportunity.approvedRevision()).isEqualTo(2);

    assertThatThrownBy(
            () ->
                opportunity.activatePublication(
                    0L,
                    NOW,
                    REVIEWER,
                    CORRELATION,
                    hierarchy.publisher,
                    hierarchy.channel,
                    hierarchy.environment))
        .isInstanceOf(SegregationOfDutiesException.class);

    opportunity.activatePublication(
        0L,
        NOW,
        ACTIVATOR,
        CORRELATION,
        hierarchy.publisher,
        hierarchy.channel,
        hierarchy.environment);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.PUBLISHED);
    opportunity.pause(0L, NOW, ACTIVATOR, CORRELATION);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.PAUSED);
    opportunity.resume(
        0L,
        NOW,
        ACTIVATOR,
        CORRELATION,
        hierarchy.publisher,
        hierarchy.channel,
        hierarchy.environment);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.PUBLISHED);
    opportunity.revoke(0L, "Revogar autorização interna.", NOW, ACTIVATOR, CORRELATION);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.REVOKED);
    assertThatThrownBy(
            () -> opportunity.pause(0L, NOW, ACTIVATOR, CORRELATION))
        .isInstanceOf(InvalidGovernanceTransitionException.class);
  }

  @Test
  void rejectIsTerminalAndRequiresJustification() {
    Hierarchy hierarchy = activeHierarchy();
    ContextualOpportunity opportunity = draft(hierarchy);
    opportunity.submit(0L, NOW, AUTHOR, CORRELATION);
    assertThatThrownBy(
            () -> opportunity.reject(0L, 1, "curto", NOW, REVIEWER, CORRELATION))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(
            () -> opportunity.reject(0L, 1, "<script>x</script>abcde", NOW, REVIEWER, CORRELATION))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> opportunity.reject(0L, 1, null, NOW, REVIEWER, CORRELATION))
        .isInstanceOf(JustificationRequiredException.class);
    opportunity.reject(0L, 1, "Conteúdo editorial insuficiente.", NOW, REVIEWER, CORRELATION);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.REVOKED);
    assertThatThrownBy(() -> opportunity.submit(0L, NOW, AUTHOR, CORRELATION))
        .isInstanceOf(InvalidGovernanceTransitionException.class);
  }

  @Test
  void reviewRejectsOldRevisionAndStaleVersion() {
    Hierarchy hierarchy = activeHierarchy();
    ContextualOpportunity opportunity = draft(hierarchy);
    opportunity.submit(0L, NOW, AUTHOR, CORRELATION);
    assertThatThrownBy(() -> opportunity.approve(1L, 1, NOW, REVIEWER, CORRELATION))
        .isInstanceOf(OptimisticConcurrencyException.class);
    assertThatThrownBy(() -> opportunity.approve(0L, 9, NOW, REVIEWER, CORRELATION))
        .isInstanceOf(RevisionNotCurrentException.class);
  }

  @Test
  void windowEdgesAndExpire() {
    Hierarchy hierarchy = activeHierarchy();
    ContextualOpportunity future =
        ContextualOpportunity.create(
            UUID.randomUUID(),
            hierarchy.publisher,
            hierarchy.channel,
            hierarchy.environment,
            ResourceKey.parse("future-win"),
            windowed("Janela futura de publicação", NOW.plusSeconds(60), NOW.plusSeconds(120)),
            NOW,
            AUTHOR);
    future.submit(0L, NOW, AUTHOR, CORRELATION);
    future.approve(0L, 1, NOW, REVIEWER, CORRELATION);
    assertThatThrownBy(
            () ->
                future.activatePublication(
                    0L,
                    NOW,
                    ACTIVATOR,
                    CORRELATION,
                    hierarchy.publisher,
                    hierarchy.channel,
                    hierarchy.environment))
        .isInstanceOf(PublicationWindowNotOpenException.class);

    ContextualOpportunity bounded =
        ContextualOpportunity.create(
            UUID.randomUUID(),
            hierarchy.publisher,
            hierarchy.channel,
            hierarchy.environment,
            ResourceKey.parse("open-win"),
            windowed("Janela aberta de publicação", NOW, NOW.plusSeconds(60)),
            NOW,
            AUTHOR);
    bounded.submit(0L, NOW, AUTHOR, CORRELATION);
    bounded.approve(0L, 1, NOW, REVIEWER, CORRELATION);
    bounded.activatePublication(
        0L,
        NOW,
        ACTIVATOR,
        CORRELATION,
        hierarchy.publisher,
        hierarchy.channel,
        hierarchy.environment);
    assertThatThrownBy(() -> bounded.expire(0L, NOW, ACTIVATOR, CORRELATION))
        .isInstanceOf(PublicationNotExpiredException.class);
    bounded.expire(0L, NOW.plusSeconds(60), ACTIVATOR, CORRELATION);
    assertThat(bounded.status()).isEqualTo(OpportunityStatus.EXPIRED);
  }

  @Test
  void parentSuspendDoesNotMutatePublishedStatus() {
    Hierarchy hierarchy = activeHierarchy();
    ContextualOpportunity opportunity = draft(hierarchy);
    opportunity.submit(0L, NOW, AUTHOR, CORRELATION);
    opportunity.approve(0L, 1, NOW, REVIEWER, CORRELATION);
    opportunity.activatePublication(
        0L,
        NOW,
        ACTIVATOR,
        CORRELATION,
        hierarchy.publisher,
        hierarchy.channel,
        hierarchy.environment);
    hierarchy.environment.transitionTo(
        LifecycleStatus.SUSPENDED, hierarchy.publisher, hierarchy.channel, NOW.plusSeconds(2), AUTHOR);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.PUBLISHED);
    assertThat(
            opportunity.effectivelyPublished(
                hierarchy.publisher, hierarchy.channel, hierarchy.environment, NOW))
        .isFalse();
    opportunity.pause(0L, NOW, ACTIVATOR, CORRELATION);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.PAUSED);
    assertThatThrownBy(
            () ->
                opportunity.resume(
                    0L,
                    NOW,
                    ACTIVATOR,
                    CORRELATION,
                    hierarchy.publisher,
                    hierarchy.channel,
                    hierarchy.environment))
        .isInstanceOf(NotEffectivelyPublishableException.class);
    assertThat(opportunity.status()).isEqualTo(OpportunityStatus.PAUSED);
  }

  @Test
  void availableActionsRespectStateWindowAndParents() {
    Hierarchy hierarchy = activeHierarchy();
    ContextualOpportunity opportunity = draft(hierarchy);
    assertThat(
            OpportunityGovernanceActions.available(
                opportunity, hierarchy.publisher, hierarchy.channel, hierarchy.environment, NOW))
        .containsExactly(GovernanceAction.SUBMIT);
    opportunity.submit(0L, NOW, AUTHOR, CORRELATION);
    assertThat(
            OpportunityGovernanceActions.available(
                opportunity, hierarchy.publisher, hierarchy.channel, hierarchy.environment, NOW))
        .containsExactly(
            GovernanceAction.RETURN_FOR_CHANGES, GovernanceAction.APPROVE, GovernanceAction.REJECT);
  }

  private static ContextualOpportunity draft(Hierarchy hierarchy) {
    return ContextualOpportunity.create(
        UUID.randomUUID(),
        hierarchy.publisher,
        hierarchy.channel,
        hierarchy.environment,
        ResourceKey.parse("crop-risk"),
        staticContent("Avaliar proteção agrícola"),
        NOW,
        AUTHOR);
  }

  private static OpportunityContent staticContent(String title) {
    return windowed(title, null, null);
  }

  private static OpportunityContent windowed(String title, Instant from, Instant until) {
    return OpportunityContent.parse(
        title,
        ContextMode.STATIC,
        "Resumo estático de contexto.",
        "Objetivo estático de avaliação.",
        "Avaliar",
        from,
        until,
        List.of());
  }

  private static Hierarchy activeHierarchy() {
    Publisher publisher =
        Publisher.create(
            UUID.randomUUID(),
            ResourceKey.parse("acme-" + UUID.randomUUID().toString().substring(0, 8)),
            DisplayName.parse("Acme"),
            NOW,
            AUTHOR);
    publisher.transitionTo(LifecycleStatus.ACTIVE, NOW.plusSeconds(1), AUTHOR);
    Channel channel =
        Channel.create(
            UUID.randomUUID(),
            publisher,
            ResourceKey.parse("portal"),
            DisplayName.parse("Portal"),
            ChannelType.WEBSITE,
            NOW,
            AUTHOR);
    channel.transitionTo(LifecycleStatus.ACTIVE, publisher, NOW.plusSeconds(1), AUTHOR);
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
            AUTHOR);
    environment.transitionTo(LifecycleStatus.ACTIVE, publisher, channel, NOW.plusSeconds(1), AUTHOR);
    return new Hierarchy(publisher, channel, environment);
  }

  private record Hierarchy(Publisher publisher, Channel channel, ContextualEnvironment environment) {}
}
