package br.com.segsense.domain.identity;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class IdentityModelTest {

  @Test
  void actorNormalizesAndFreezesRoles() {
    Actor actor = Actor.of("  subject-1  ", ActorType.USER, Set.of(" reader ", "editor"));

    assertThat(actor.subjectId()).isEqualTo("subject-1");
    assertThat(actor.type()).isEqualTo(ActorType.USER);
    assertThat(actor.roles()).containsExactlyInAnyOrder("reader", "editor");
    assertThatThrownBy(() -> actor.roles().add("admin"))
        .isInstanceOf(UnsupportedOperationException.class);
  }

  @Test
  void actorRejectsBlankSubjectAndRoles() {
    assertThatThrownBy(() -> Actor.of(" ", ActorType.USER, Set.of()))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> Actor.of("subject-1", ActorType.USER, Set.of(" ")))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> Actor.of("subject-1", null, Set.of()))
        .isInstanceOf(NullPointerException.class);
  }

  @Test
  void serviceActorIsDistinctFromUser() {
    Actor service = Actor.of("batch-job", ActorType.SERVICE, Set.of());
    assertThat(service.type()).isEqualTo(ActorType.SERVICE);
    assertThat(service.roles()).isEmpty();
  }

  @Test
  void applicationIdentityDoesNotAcceptBlankValues() {
    ApplicationIdentity identity = ApplicationIdentity.of("  SEGSENSE  ");
    assertThat(identity.applicationId()).isEqualTo("SEGSENSE");
    assertThatThrownBy(() -> ApplicationIdentity.of("")).isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void channelContextDoesNotAcceptBlankValues() {
    ChannelContext channel = ChannelContext.of("  portal-a  ");
    assertThat(channel.channelId()).isEqualTo("portal-a");
    assertThatThrownBy(() -> ChannelContext.of(null)).isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void mutatingSourceRoleSetDoesNotChangeActor() {
    Set<String> source = new HashSet<>();
    source.add("reader");
    Actor actor = Actor.of("subject-1", ActorType.USER, source);
    source.add("admin");
    assertThat(actor.roles()).containsExactly("reader");
  }
}
