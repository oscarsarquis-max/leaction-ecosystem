package br.com.segsense.domain.catalog;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class CatalogAggregateTest {

  private static final Instant NOW = Instant.parse("2026-09-04T12:00:00Z");
  private static final String ACTOR = "catalog-tester";

  @Test
  void publisherNormalizesKeyAndStartsDraft() {
    Publisher publisher =
        Publisher.create(
            UUID.randomUUID(),
            ResourceKey.parse("  Acme-Portal  "),
            DisplayName.parse("  Acme  "),
            NOW,
            ACTOR);

    assertThat(publisher.key().value()).isEqualTo("acme-portal");
    assertThat(publisher.name().value()).isEqualTo("Acme");
    assertThat(publisher.status()).isEqualTo(LifecycleStatus.DRAFT);
    assertThat(publisher.effectivelyAvailable()).isFalse();
    assertThat(publisher.version()).isZero();
    assertThat(publisher.createdBy()).isEqualTo(ACTOR);
  }

  @Test
  void keyRemainsImmutableAfterCreate() {
    ResourceKey key = ResourceKey.parse("site-um");
    Publisher publisher =
        Publisher.create(UUID.randomUUID(), key, DisplayName.parse("Site Um"), NOW, ACTOR);
    assertThat(publisher.key()).isSameAs(key);
    assertThat(publisher.key().value()).isEqualTo("site-um");
  }

  @Test
  void rejectsInvalidKeysAndBlankNames() {
    assertThatThrownBy(() -> ResourceKey.parse("AB"))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> ResourceKey.parse("1abc"))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> ResourceKey.parse("ab_c"))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> DisplayName.parse("  "))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> DisplayName.parse("ab"))
        .isInstanceOf(CatalogValidationException.class);
  }

  @Test
  void publisherTransitionsFollowMatrixAndNeverReturnToDraft() {
    Publisher publisher = publisher("acme");
    publisher.transitionTo(LifecycleStatus.ACTIVE, NOW.plusSeconds(1), ACTOR);
    assertThat(publisher.status()).isEqualTo(LifecycleStatus.ACTIVE);
    assertThat(publisher.effectivelyAvailable()).isTrue();

    publisher.transitionTo(LifecycleStatus.SUSPENDED, NOW.plusSeconds(2), ACTOR);
    assertThat(publisher.status()).isEqualTo(LifecycleStatus.SUSPENDED);
    assertThat(publisher.effectivelyAvailable()).isFalse();

    publisher.transitionTo(LifecycleStatus.ACTIVE, NOW.plusSeconds(3), ACTOR);
    assertThat(publisher.status()).isEqualTo(LifecycleStatus.ACTIVE);

    assertThatThrownBy(() -> publisher.transitionTo(LifecycleStatus.DRAFT, NOW, ACTOR))
        .isInstanceOf(InvalidStateTransitionException.class);
  }

  @Test
  void channelActivationRequiresActivePublisherAndDoesNotMutateChildrenOnParentSuspend() {
    Publisher publisher = publisher("acme");
    Channel channel = channel(publisher, "web");
    assertThatThrownBy(
            () -> channel.transitionTo(LifecycleStatus.ACTIVE, publisher, NOW, ACTOR))
        .isInstanceOf(InvalidStateTransitionException.class);

    publisher.transitionTo(LifecycleStatus.ACTIVE, NOW, ACTOR);
    channel.transitionTo(LifecycleStatus.ACTIVE, publisher, NOW, ACTOR);
    assertThat(channel.status()).isEqualTo(LifecycleStatus.ACTIVE);
    assertThat(channel.effectivelyAvailable(publisher)).isTrue();

    publisher.transitionTo(LifecycleStatus.SUSPENDED, NOW, ACTOR);
    assertThat(channel.status()).isEqualTo(LifecycleStatus.ACTIVE);
    assertThat(channel.effectivelyAvailable(publisher)).isFalse();

    publisher.transitionTo(LifecycleStatus.ACTIVE, NOW, ACTOR);
    assertThat(channel.status()).isEqualTo(LifecycleStatus.ACTIVE);
    assertThat(channel.effectivelyAvailable(publisher)).isTrue();
  }

  @Test
  void reactivatingPublisherDoesNotChangeSuspendedChannel() {
    Publisher publisher = publisher("acme");
    publisher.transitionTo(LifecycleStatus.ACTIVE, NOW, ACTOR);
    Channel channel = channel(publisher, "web");
    channel.transitionTo(LifecycleStatus.ACTIVE, publisher, NOW, ACTOR);
    channel.transitionTo(LifecycleStatus.SUSPENDED, publisher, NOW, ACTOR);

    publisher.transitionTo(LifecycleStatus.SUSPENDED, NOW, ACTOR);
    publisher.transitionTo(LifecycleStatus.ACTIVE, NOW, ACTOR);

    assertThat(channel.status()).isEqualTo(LifecycleStatus.SUSPENDED);
    assertThat(channel.effectivelyAvailable(publisher)).isFalse();
  }

  @Test
  void environmentActivationRequiresActivePublisherAndChannel() {
    Publisher publisher = publisher("acme");
    Channel channel = channel(publisher, "web");
    ContextualEnvironment environment = environment(publisher, channel, "home");

    publisher.transitionTo(LifecycleStatus.ACTIVE, NOW, ACTOR);
    assertThatThrownBy(
            () ->
                environment.transitionTo(
                    LifecycleStatus.ACTIVE, publisher, channel, NOW, ACTOR))
        .isInstanceOf(InvalidStateTransitionException.class);

    channel.transitionTo(LifecycleStatus.ACTIVE, publisher, NOW, ACTOR);
    environment.transitionTo(LifecycleStatus.ACTIVE, publisher, channel, NOW, ACTOR);
    assertThat(environment.effectivelyAvailable(publisher, channel)).isTrue();

    channel.transitionTo(LifecycleStatus.SUSPENDED, publisher, NOW, ACTOR);
    assertThat(environment.status()).isEqualTo(LifecycleStatus.ACTIVE);
    assertThat(environment.effectivelyAvailable(publisher, channel)).isFalse();
  }

  @Test
  void optimisticVersionMismatchIsRejected() {
    Publisher publisher = publisher("acme");
    assertThatThrownBy(() -> publisher.requireExpectedVersion(3))
        .isInstanceOf(OptimisticConcurrencyException.class);
    publisher.requireExpectedVersion(0);
  }

  @Test
  void canonicalUrlRejectsUnsafeValues() {
    assertThat(CanonicalUrl.parseOptional(null)).isEmpty();
    assertThat(CanonicalUrl.parseOptional("  ")).isEmpty();
    assertThat(CanonicalUrl.parse("https://example.com/artigo").value())
        .isEqualTo("https://example.com/artigo");

    assertThatThrownBy(() -> CanonicalUrl.parse("http://example.com"))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> CanonicalUrl.parse("https://user:pass@example.com/x"))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> CanonicalUrl.parse("https://example.com/x?q=1"))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> CanonicalUrl.parse("https://example.com/x#frag"))
        .isInstanceOf(CatalogValidationException.class);
    assertThatThrownBy(() -> CanonicalUrl.parse("/relativo"))
        .isInstanceOf(CatalogValidationException.class);
  }

  @Test
  void channelLookupRejectsMismatchedPublisherOnTransition() {
    Publisher one = publisher("one");
    Publisher two =
        Publisher.create(
            UUID.randomUUID(), ResourceKey.parse("two"), DisplayName.parse("Dois"), NOW, ACTOR);
    Channel channel = channel(one, "web");
    assertThatThrownBy(() -> channel.transitionTo(LifecycleStatus.ACTIVE, two, NOW, ACTOR))
        .isInstanceOf(ResourceNotFoundException.class);
  }

  private static Publisher publisher(String key) {
    return Publisher.create(
        UUID.randomUUID(), ResourceKey.parse(key), DisplayName.parse("Nome " + key), NOW, ACTOR);
  }

  private static Channel channel(Publisher publisher, String key) {
    return Channel.create(
        UUID.randomUUID(),
        publisher,
        ResourceKey.parse(key),
        DisplayName.parse("Canal " + key),
        ChannelType.WEBSITE,
        NOW,
        ACTOR);
  }

  private static ContextualEnvironment environment(
      Publisher publisher, Channel channel, String key) {
    return ContextualEnvironment.create(
        UUID.randomUUID(),
        publisher,
        channel,
        ResourceKey.parse(key),
        DisplayName.parse("Ambiente " + key),
        EnvironmentType.PAGE,
        null,
        NOW,
        ACTOR);
  }
}
