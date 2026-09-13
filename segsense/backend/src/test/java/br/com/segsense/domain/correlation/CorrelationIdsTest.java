package br.com.segsense.domain.correlation;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class CorrelationIdsTest {

  @Test
  void parsesValidUuid() {
    assertThat(CorrelationIds.parseValid("33333333-3333-3333-3333-333333333333")).isPresent();
  }

  @Test
  void rejectsBlankOrInvalidValues() {
    assertThat(CorrelationIds.parseValid(null)).isEmpty();
    assertThat(CorrelationIds.parseValid("")).isEmpty();
    assertThat(CorrelationIds.parseValid("not-a-uuid")).isEmpty();
  }
}
