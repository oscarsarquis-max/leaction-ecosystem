package br.com.actionfinance.application.overview;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

public record OverviewFacts(
        boolean payAuthorized,
        List<MethodAmount> sales,
        FeeReading fees,
        List<CategoryAmount> expenses,
        CashReading cash,
        List<OpenTitle> openTitles,
        int reviewOccurrences,
        int reconciliationPending,
        int statementLines,
        Instant lastPaySync,
        Instant lastStatement,
        String accountName) {

    public record MethodAmount(String method, long minor) {}

    public record FeeReading(int lineCount, int measuredCount, long feeMinor) {}

    public record CategoryAmount(String name, long minor) {}

    public record CashReading(String state, Long minor) {}

    public record OpenTitle(String direction, String description, LocalDate due, long remainingMinor) {}
}
