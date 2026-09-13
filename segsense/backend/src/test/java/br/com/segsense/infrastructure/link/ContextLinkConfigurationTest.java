package br.com.segsense.infrastructure.link;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;
import org.springframework.core.env.Environment;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.mock.env.MockEnvironment;

class ContextLinkConfigurationTest {

  @Test
  void localHttpLoopbackIsAcceptedAndTrailingSlashRemoved() {
    assertThat(ContextLinkConfiguration.normalize("http://127.0.0.1:5178/", env("local")))
        .isEqualTo("http://127.0.0.1:5178");
  }

  @Test
  void testHttpLoopbackIsAccepted() {
    assertThat(ContextLinkConfiguration.normalize("http://127.0.0.1:5178", env("test")))
        .isEqualTo("http://127.0.0.1:5178");
  }

  @Test
  void localAndTestTogetherAllowHttpLoopback() {
    assertThat(ContextLinkConfiguration.normalize("http://127.0.0.1:5178", env("local", "test")))
        .isEqualTo("http://127.0.0.1:5178");
  }

  @Test
  void rejectsUserinfoFragmentQueryAndEmptyHost() {
    Environment environment = env("test");
    assertThatThrownBy(() -> ContextLinkConfiguration.normalize("http://user:pass@127.0.0.1:5178", environment))
        .isInstanceOf(IllegalStateException.class);
    assertThatThrownBy(() -> ContextLinkConfiguration.normalize("http://127.0.0.1:5178#frag", environment))
        .isInstanceOf(IllegalStateException.class);
    assertThatThrownBy(() -> ContextLinkConfiguration.normalize("http://127.0.0.1:5178?q=1", environment))
        .isInstanceOf(IllegalStateException.class);
    assertThatThrownBy(() -> ContextLinkConfiguration.normalize("http:///path", environment))
        .isInstanceOf(IllegalStateException.class);
  }

  @Test
  void noActiveProfileRejectsHttp() {
    assertThatThrownBy(
            () -> ContextLinkConfiguration.normalize("http://127.0.0.1:5178", new StandardEnvironment()))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("https");
  }

  @Test
  void defaultProfileRejectsHttp() {
    assertThatThrownBy(() -> ContextLinkConfiguration.normalize("http://127.0.0.1:5178", env("default")))
        .isInstanceOf(IllegalStateException.class);
  }

  @Test
  void productionProfileRequiresHttps() {
    assertThatThrownBy(() -> ContextLinkConfiguration.normalize("http://127.0.0.1:5178", env("prod")))
        .isInstanceOf(IllegalStateException.class);
  }

  @Test
  void unknownProfileRejectsHttp() {
    assertThatThrownBy(() -> ContextLinkConfiguration.normalize("http://127.0.0.1:5178", env("staging")))
        .isInstanceOf(IllegalStateException.class);
  }

  @Test
  void localCombinedWithProdRejectsHttp() {
    assertThatThrownBy(
            () -> ContextLinkConfiguration.normalize("http://127.0.0.1:5178", env("local", "prod")))
        .isInstanceOf(IllegalStateException.class);
  }

  @Test
  void httpsIsAcceptedForAnyProfileIncludingNone() {
    assertThat(ContextLinkConfiguration.normalize("https://links.example.com/", new StandardEnvironment()))
        .isEqualTo("https://links.example.com");
    assertThat(ContextLinkConfiguration.normalize("https://links.example.com/", env("prod")))
        .isEqualTo("https://links.example.com");
    assertThat(ContextLinkConfiguration.normalize("https://links.example.com/", env("unknown")))
        .isEqualTo("https://links.example.com");
    assertThat(ContextLinkConfiguration.normalize("https://links.example.com/", env("local")))
        .isEqualTo("https://links.example.com");
  }

  private static Environment env(String... profiles) {
    MockEnvironment environment = new MockEnvironment();
    environment.setActiveProfiles(profiles);
    return environment;
  }
}
