package br.com.actionfinance.domain;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class MoneyAmountTest {

    @Test
    void parsesDigitStringsAndRejectsDecimals() {
        assertThat(MoneyAmount.parseApi("123456").orElseThrow().toApiString()).isEqualTo("123456");
        assertThat(MoneyAmount.parseApi(" ").isEmpty()).isTrue();
        assertThatThrownBy(() -> MoneyAmount.parseApi("12.50")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> MoneyAmount.parseApi("0")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> MoneyAmount.parseApi("01")).isInstanceOf(IllegalArgumentException.class);
        assertThat(MoneyAmount.ofMinor(new BigDecimal("999")).toApiString()).isEqualTo("999");
        assertThat(MoneyAmount.parseSignedApi("0").orElseThrow().toApiString()).isEqualTo("0");
        assertThat(MoneyAmount.parseSignedApi("-2500").orElseThrow().toApiString()).isEqualTo("-2500");
        assertThat(MoneyAmount.ofSignedMinor(new BigDecimal("-10")).toApiString()).isEqualTo("-10");
    }
}
