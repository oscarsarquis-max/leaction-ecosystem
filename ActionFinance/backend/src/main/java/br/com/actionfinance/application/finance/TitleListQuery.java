package br.com.actionfinance.application.finance;

import br.com.actionfinance.domain.TitleStatus;

import java.time.LocalDate;
import java.util.Set;
import java.util.UUID;

public record TitleListQuery(
        String search,
        TitleStatus status,
        boolean allStatuses,
        LocalDate dueFrom,
        LocalDate dueTo,
        UUID categoryId,
        boolean overdueOnly,
        FinancialFilter financial,
        int page,
        int size) {

    public static final Set<Integer> ALLOWED_SIZES = Set.of(20, 50);
    public static final Set<String> ALLOWED_SORT = Set.of("dueDate,id");
}
