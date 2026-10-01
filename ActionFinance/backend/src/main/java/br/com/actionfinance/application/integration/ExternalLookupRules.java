package br.com.actionfinance.application.integration;

import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.domain.MoneyAmount;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

public final class ExternalLookupRules {

    private ExternalLookupRules() {}

    public static String fingerprint(UUID companyId, String reference, UUID titleId) {
        return sha256(companyId + "|" + reference + "|ACTIONHUB_PAY|" + titleId);
    }

    public static boolean sameLookupIdentity(String stored, UUID companyId, String reference, UUID titleId) {
        if (stored == null) {
            return false;
        }
        return stored.equals(fingerprint(companyId, reference, titleId))
                || stored.equals(sha256(companyId + "|" + reference + "|ACTIONHUB_PAY"));
    }

    private static String sha256(String value) {
        try {
            return HexFormat.of()
                    .formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    public static BigDecimal requireAmountMinor(Object raw) {
        if (raw == null) {
            throw ValidationException.of("amountMinor", "O valor observado veio ausente.");
        }
        String digits = digitsOf(raw);
        try {
            return MoneyAmount.parseApi(digits)
                    .orElseThrow(() -> ValidationException.of("amountMinor", "O valor observado é inválido."))
                    .minorUnits();
        } catch (IllegalArgumentException ex) {
            throw ValidationException.of("amountMinor", "O valor observado é inválido.");
        }
    }

    static String digitsOf(Object raw) {
        if (raw instanceof String text) {
            return text.trim();
        }
        if (raw instanceof BigDecimal decimal) {
            if (decimal.scale() > 0) {
                throw ValidationException.of("amountMinor", "O valor observado contém fração.");
            }
            return decimal.toPlainString();
        }
        if (raw instanceof Integer || raw instanceof Long || raw instanceof Short) {
            return String.valueOf(raw);
        }
        throw ValidationException.of("amountMinor", "O valor observado é inválido.");
    }

    public static Instant providerObservedAt(Object raw) {
        if (raw == null) {
            return null;
        }
        try {
            return Instant.parse(String.valueOf(raw));
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    public static boolean staleObservation(Instant stored, Instant incoming) {
        return stored != null && incoming != null && incoming.isBefore(stored);
    }

    public static boolean financialChanged(ExternalLookupView before, ExternalLookupView after) {
        if (before == null || after == null) {
            return after != null;
        }
        return !java.util.Objects.equals(before.externalStatus(), after.externalStatus())
                || !java.util.Objects.equals(before.amountMinor(), after.amountMinor())
                || !java.util.Objects.equals(before.currency(), after.currency())
                || !java.util.Objects.equals(before.observedAt(), after.observedAt());
    }

    public static ExternalLookupView applyAttempt(
            ExternalLookupView current, SpiderInteractionClient.SpiderLookupResult result, Instant attemptAt) {
        return applyAttempt(current, result, attemptAt, current.correlationId());
    }

    public static ExternalLookupView applyAttempt(
            ExternalLookupView current,
            SpiderInteractionClient.SpiderLookupResult result,
            Instant attemptAt,
            String expectedCorrelation) {
        if (!result.available() || "UNAVAILABLE".equals(result.status()) || "PROVIDER_UNAVAILABLE".equals(result.status())) {
            String transportError =
                    result.errorMessage() == null || result.errorMessage().isBlank()
                            ? "Não foi possível atualizar. A observação anterior foi preservada."
                            : result.errorMessage();
            return withAttempt(
                    current,
                    "UNAVAILABLE",
                    "UNAVAILABLE",
                    transportError,
                    attemptAt,
                    current.spiderDecisionId());
        }
        if ("REJECTED".equals(result.status())) {
            return withAttempt(current, "REJECTED", "CONFLICT", "A Spider recusou a consulta.", attemptAt, result.decisionId());
        }
        Map<String, Object> summary = result.summary() == null ? Map.of() : result.summary();
        if (!identityMatches(current, result, summary, expectedCorrelation)) {
            return withAttempt(
                    current,
                    "INVALID",
                    "CONFLICT",
                    "A resposta não confere com a consulta enviada.",
                    attemptAt,
                    result.decisionId());
        }
        String mapped;
        BigDecimal amount;
        String currency;
        try {
            mapped = mapExternal(text(summary.get("externalStatus")));
            amount = requireAmountMinor(summary.get("amountMinor"));
            currency = requireCurrency(text(summary.get("currency")));
        } catch (ValidationException ex) {
            return withAttempt(current, "INVALID", "CONFLICT", ex.getMessage(), attemptAt, result.decisionId());
        }
        Instant originObserved = providerObservedAt(first(summary.get("providerObservedAt"), summary.get("observedAt")));
        if (staleObservation(current.observedAt(), originObserved)) {
            return withAttempt(current, "DELIVERED", "DELIVERED", "Resposta atrasada ignorada.", attemptAt, result.decisionId());
        }
        boolean diverge =
                (current.amountMinor() != null && amount.compareTo(current.amountMinor()) != 0)
                        || (current.currency() != null && !current.currency().equals(currency));
        if (diverge) {
            return new ExternalLookupView(
                    current.id(),
                    current.companyId(),
                    current.titleId(),
                    current.capability(),
                    current.originSystem(),
                    current.externalReference(),
                    current.amountMinor(),
                    current.currency(),
                    "REVIEW_REQUIRED",
                    "DELIVERED",
                    current.correlationId(),
                    result.decisionId(),
                    current.providerReference(),
                    text(summary.get("origin")),
                    "Divergência de valor ou moeda em relação à observação anterior.",
                    current.observedAt(),
                    attemptAt,
                    attemptAt,
                    "CONFLICT",
                    current.lastAttemptId(),
                    current.version(),
                    false,
                    true);
        }
        return new ExternalLookupView(
                current.id(),
                current.companyId(),
                current.titleId(),
                current.capability(),
                current.originSystem(),
                current.externalReference(),
                amount,
                currency,
                mapped,
                "DELIVERED",
                current.correlationId(),
                result.decisionId(),
                text(summary.get("providerReference")),
                text(summary.get("origin")),
                null,
                originObserved,
                attemptAt,
                attemptAt,
                "DELIVERED",
                current.lastAttemptId(),
                current.version(),
                false,
                true);
    }

    static boolean identityMatches(
            ExternalLookupView current,
            SpiderInteractionClient.SpiderLookupResult result,
            Map<String, Object> summary,
            String expectedCorrelation) {
        if (result.correlationId() != null
                && expectedCorrelation != null
                && !result.correlationId().equals(expectedCorrelation)) {
            return false;
        }
        String reference = text(summary.get("providerReference"));
        if (reference != null && !reference.equals(current.externalReference())) {
            return false;
        }
        String capability = result.capabilityId();
        if (capability != null && !"LOOKUP_ACTIONHUB_PAYMENT".equals(capability)) {
            return false;
        }
        String company = text(summary.get("companyId"));
        if (company != null && current.companyId() != null && !company.equals(current.companyId().toString())) {
            return false;
        }
        return true;
    }

    static String mapExternal(String providerStatus) {
        String normalized = providerStatus == null ? "" : providerStatus.trim().toUpperCase(Locale.ROOT);
        return switch (normalized) {
            case "PAID", "APPROVED", "CONFIRMED" -> "CONFIRMED";
            case "CANCELLED", "CANCELED", "REJECTED", "FAILED", "REFUSED" -> "REFUSED";
            case "PENDING", "IN_PROCESS", "IN_PROGRESS" -> "IN_PROGRESS";
            case "REFUNDED", "CHARGED_BACK" -> "REFUNDED";
            case "REVIEW", "INCONSISTENT", "REVIEW_REQUIRED" -> "REVIEW_REQUIRED";
            default -> "REVIEW_REQUIRED";
        };
    }

    private static ExternalLookupView withAttempt(
            ExternalLookupView current,
            String attempt,
            String delivery,
            String error,
            Instant attemptAt,
            String decisionId) {
        return new ExternalLookupView(
                current.id(),
                current.companyId(),
                current.titleId(),
                current.capability(),
                current.originSystem(),
                current.externalReference(),
                current.amountMinor(),
                current.currency(),
                current.externalStatus(),
                delivery,
                current.correlationId(),
                decisionId == null ? current.spiderDecisionId() : decisionId,
                current.providerReference(),
                current.providerOrigin(),
                error,
                current.observedAt(),
                attemptAt,
                attemptAt,
                attempt,
                current.lastAttemptId(),
                current.version(),
                false,
                true);
    }

    private static String requireCurrency(String currency) {
        if (currency == null || currency.isBlank()) {
            throw ValidationException.of("currency", "A moeda observada veio ausente.");
        }
        if (!"BRL".equals(currency)) {
            throw ValidationException.of("currency", "A moeda observada não é suportada neste recorte.");
        }
        return currency;
    }

    private static Object first(Object left, Object right) {
        return left != null ? left : right;
    }

    private static String text(Object value) {
        return value == null ? null : String.valueOf(value);
    }
}
