package br.com.segsense.inbound.http.link;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class PublicTokenRedactingFilterTest {

  @Test
  void redactsOpaqueTokenSegment() {
    assertThat(
            PublicTokenRedactingFilter.redact(
                "/api/v1/public/context-links/AbCdefGhijkLmnoPqrstuvWxyz0123456789_-abc"))
        .isEqualTo("/api/v1/public/context-links/[redacted]");
    assertThat(PublicTokenRedactingFilter.redact("/api/v1/system/info")).isEqualTo("/api/v1/system/info");
  }
}
