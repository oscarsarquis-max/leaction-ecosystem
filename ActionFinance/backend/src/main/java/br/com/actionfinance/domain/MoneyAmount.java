package br.com.actionfinance.domain;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.Optional;

public final class MoneyAmount {

    public static final BigDecimal MAX_MINOR = new BigDecimal("9999999999999999999");

    private final BigDecimal minorUnits;

    private MoneyAmount(BigDecimal minorUnits) {
        this.minorUnits = minorUnits;
    }

    public static Optional<MoneyAmount> parseApi(String raw) {
        if (raw == null || raw.isBlank()) {
            return Optional.empty();
        }
        String trimmed = raw.trim();
        if (!trimmed.matches("[0-9]+")) {
            throw new IllegalArgumentException("amount-not-digits");
        }
        if (trimmed.length() > 1 && trimmed.startsWith("0")) {
            throw new IllegalArgumentException("amount-leading-zero");
        }
        BigDecimal value = new BigDecimal(trimmed);
        if (value.scale() != 0 || value.signum() <= 0 || value.compareTo(MAX_MINOR) > 0) {
            throw new IllegalArgumentException("amount-out-of-range");
        }
        return Optional.of(new MoneyAmount(value));
    }

    public static Optional<MoneyAmount> parseSignedApi(String raw) {
        if (raw == null || raw.isBlank()) {
            return Optional.empty();
        }
        String trimmed = raw.trim();
        boolean negative = trimmed.startsWith("-");
        String digits = negative ? trimmed.substring(1) : trimmed;
        if (!digits.matches("[0-9]+")) {
            throw new IllegalArgumentException("amount-not-digits");
        }
        if (digits.length() > 1 && digits.startsWith("0")) {
            throw new IllegalArgumentException("amount-leading-zero");
        }
        BigDecimal value = new BigDecimal(digits);
        if (value.scale() != 0 || value.compareTo(MAX_MINOR) > 0) {
            throw new IllegalArgumentException("amount-out-of-range");
        }
        return Optional.of(new MoneyAmount(negative && value.signum() != 0 ? value.negate() : value));
    }

    public static MoneyAmount ofSignedMinor(BigDecimal stored) {
        if (stored == null) {
            throw new IllegalArgumentException("amount-missing");
        }
        BigDecimal normalized = stored.stripTrailingZeros();
        if (normalized.scale() > 0) {
            throw new IllegalArgumentException("amount-out-of-range");
        }
        BigDecimal abs = normalized.abs();
        if (abs.compareTo(MAX_MINOR) > 0) {
            throw new IllegalArgumentException("amount-out-of-range");
        }
        return new MoneyAmount(normalized.setScale(0));
    }

    public static MoneyAmount ofMinor(BigDecimal stored) {
        if (stored == null) {
            throw new IllegalArgumentException("amount-missing");
        }
        BigDecimal normalized = stored.stripTrailingZeros();
        if (normalized.scale() > 0 || normalized.signum() <= 0 || normalized.compareTo(MAX_MINOR) > 0) {
            throw new IllegalArgumentException("amount-out-of-range");
        }
        return new MoneyAmount(normalized.setScale(0));
    }

    public BigDecimal minorUnits() {
        return minorUnits;
    }

    public BigInteger toBigInteger() {
        return minorUnits.toBigIntegerExact();
    }

    public String toApiString() {
        return minorUnits.toPlainString();
    }
}
