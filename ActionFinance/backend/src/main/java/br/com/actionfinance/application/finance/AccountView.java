package br.com.actionfinance.application.finance;

import br.com.actionfinance.domain.AccountType;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public record AccountView(
        UUID id,
        UUID tenantId,
        UUID companyId,
        String companyName,
        String code,
        String name,
        AccountType type,
        String currency,
        boolean active,
        LocalDate openedOn,
        BigDecimal currentBalanceMinor,
        long version,
        Instant createdAt,
        Instant updatedAt,
        boolean openingRecorded,
        AccountProfile profile,
        List<OriginLinkView> originLinks) {

    public AccountView {
        if (profile == null) {
            profile = AccountProfile.empty();
        }
        originLinks = originLinks == null ? List.of() : List.copyOf(originLinks);
    }

    public AccountView withDetails(AccountProfile nextProfile, List<OriginLinkView> links) {
        return new AccountView(
                id, tenantId, companyId, companyName, code, name, type, currency, active, openedOn,
                currentBalanceMinor, version, createdAt, updatedAt, openingRecorded, nextProfile, links);
    }

    public record HistoryEntry(
            UUID id,
            long accountVersion,
            String action,
            UUID actorId,
            Instant occurredAt,
            String changesJson) {}

    public record Page(List<AccountView> items) {}
}
