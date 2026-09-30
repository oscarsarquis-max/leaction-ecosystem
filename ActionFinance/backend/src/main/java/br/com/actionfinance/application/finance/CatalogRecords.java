package br.com.actionfinance.application.finance;

import br.com.actionfinance.domain.CategoryDirection;
import br.com.actionfinance.domain.CounterpartyRole;

import java.time.Instant;
import java.util.UUID;

public final class CatalogRecords {

    private CatalogRecords() {}

    public record CounterpartyView(
            UUID id,
            UUID tenantId,
            UUID companyId,
            String code,
            String name,
            CounterpartyRole role,
            boolean active,
            long version,
            Instant createdAt,
            Instant updatedAt) {}

    public record CategoryView(
            UUID id,
            UUID tenantId,
            UUID companyId,
            String code,
            String name,
            CategoryDirection direction,
            boolean active,
            long version,
            Instant createdAt,
            Instant updatedAt) {}
}
