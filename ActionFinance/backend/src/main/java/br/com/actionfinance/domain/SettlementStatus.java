package br.com.actionfinance.domain;

import java.math.BigDecimal;

public enum SettlementStatus {
    UNSETTLED,
    PARTIAL,
    SETTLED,
    NOT_APPLICABLE;

    public static SettlementStatus derive(TitleStatus status, BigDecimal original, BigDecimal settled) {
        if (status != TitleStatus.OPEN) {
            return NOT_APPLICABLE;
        }
        BigDecimal principal = original == null ? BigDecimal.ZERO : original;
        BigDecimal done = settled == null ? BigDecimal.ZERO : settled;
        if (done.signum() == 0) {
            return UNSETTLED;
        }
        if (done.compareTo(principal) >= 0) {
            return SETTLED;
        }
        return PARTIAL;
    }
}
