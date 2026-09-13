package br.com.segsense.infrastructure.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class CorsAllowedOriginsTest {

  @Test
  void parsesLoopbackAliasesAndRejectsWildcard() {
    String[] origins =
        CorsAllowedOrigins.parse("http://127.0.0.1:5178, http://localhost:5178");
    assertThat(origins)
        .containsExactly("http://127.0.0.1:5178", "http://localhost:5178");
    assertThat(CorsAllowedOrigins.allows(origins, "http://localhost:5178")).isTrue();
    assertThat(CorsAllowedOrigins.allows(origins, "https://evil.example")).isFalse();
    assertThatThrownBy(() -> CorsAllowedOrigins.parse("*"))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> CorsAllowedOrigins.parse("https://*.example"))
        .isInstanceOf(IllegalArgumentException.class);
  }
}
