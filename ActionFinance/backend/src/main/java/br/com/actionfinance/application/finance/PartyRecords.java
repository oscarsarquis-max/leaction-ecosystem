package br.com.actionfinance.application.finance;

import br.com.actionfinance.domain.AddressUsage;
import br.com.actionfinance.domain.CounterpartyRole;
import br.com.actionfinance.domain.DocumentType;
import br.com.actionfinance.domain.OriginKind;
import br.com.actionfinance.domain.PersonKind;
import br.com.actionfinance.domain.UnitKind;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class PartyRecords {

    private PartyRecords() {}

    public record PartyListItem(
            UUID id,
            String code,
            String name,
            String tradeName,
            CounterpartyRole role,
            boolean active,
            boolean documentPending,
            String documentType,
            String documentCountry,
            String documentDisplay,
            String locality,
            OriginKind originKind,
            long version) {}

    public record PartyPage(
            List<PartyListItem> items, long totalItems, int page, int size) {}

    public record PartyUnitView(
            UUID id,
            String name,
            UnitKind unitKind,
            boolean primary,
            boolean active,
            String documentCountry,
            DocumentType documentType,
            String documentNumber,
            String documentDisplay) {}

    public record PartyAddressView(
            UUID id,
            UUID unitId,
            String country,
            String postalCode,
            String street,
            String number,
            boolean noNumber,
            String complement,
            String district,
            String municipality,
            String region,
            AddressUsage usage,
            boolean incomplete,
            boolean active) {}

    public record PartyContactView(
            UUID id,
            String name,
            String roleTitle,
            String email,
            String phone,
            boolean primary,
            boolean active) {}

    public record PartySupplyView(
            UUID id, String description, String supplyCategory, String notes, boolean active) {}

    public record PartyExternalView(
            UUID id,
            String originSystem,
            String connectionKey,
            String externalId,
            Instant observedAt) {}

    public record PartyHistoryView(
            UUID id,
            long counterpartyVersion,
            String action,
            UUID actorId,
            String actorDisplayName,
            Instant occurredAt,
            String reason) {}

    public record PartyCompleteness(
            boolean identityReady,
            boolean documentReady,
            boolean addressReady,
            boolean contactReady,
            boolean paymentReady,
            String paymentNote) {}

    public record PartyDetail(
            UUID id,
            String code,
            String name,
            String tradeName,
            PersonKind personKind,
            CounterpartyRole role,
            boolean active,
            boolean documentPending,
            String documentCountry,
            DocumentType documentType,
            String documentNumber,
            String documentDisplay,
            OriginKind originKind,
            String notes,
            long version,
            Instant createdAt,
            Instant updatedAt,
            UUID createdBy,
            UUID updatedBy,
            boolean referencedByTitles,
            PartyCompleteness completeness,
            List<PartyUnitView> units,
            List<PartyAddressView> addresses,
            List<PartyContactView> contacts,
            List<PartySupplyView> supplies,
            List<PartyExternalView> externalIdentities,
            List<PartyHistoryView> history) {}

    public record PartyCandidate(
            UUID id,
            String name,
            String tradeName,
            CounterpartyRole role,
            boolean active,
            String documentDisplay,
            String matchKind) {}

    public record ImportLineView(
            UUID id,
            int lineNo,
            String classification,
            boolean selected,
            UUID matchCounterpartyId,
            String name,
            String role,
            String documentDisplay,
            String errorMessage,
            String result) {}

    public record ImportBatchView(
            UUID id,
            String filename,
            String status,
            int totalLines,
            int newCount,
            int duplicateCount,
            int conflictCount,
            int invalidCount,
            String atomicity,
            List<ImportLineView> lines,
            ImportReport report) {}

    public record ImportReport(
            int created, int updated, int skipped, int rejected, boolean partial, String summary) {}
}
