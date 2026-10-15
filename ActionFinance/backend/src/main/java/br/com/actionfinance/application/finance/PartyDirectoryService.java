package br.com.actionfinance.application.finance;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.FinanceExceptions.CatalogConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import br.com.actionfinance.application.finance.PartyRecords.PartyCandidate;
import br.com.actionfinance.application.finance.PartyRecords.PartyCompleteness;
import br.com.actionfinance.application.finance.PartyRecords.PartyDetail;
import br.com.actionfinance.application.finance.PartyRecords.PartyListItem;
import br.com.actionfinance.application.finance.PartyRecords.PartyPage;
import br.com.actionfinance.domain.AddressUsage;
import br.com.actionfinance.domain.CounterpartyRole;
import br.com.actionfinance.domain.DocumentNumbers;
import br.com.actionfinance.domain.DocumentNumbers.NormalizedDocument;
import br.com.actionfinance.domain.DocumentType;
import br.com.actionfinance.domain.OriginKind;
import br.com.actionfinance.domain.PersonKind;
import br.com.actionfinance.domain.UnitKind;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository.AddressRow;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository.ContactRow;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository.ExternalRow;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository.PartyRow;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository.SupplyRow;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository.UnitRow;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyAddressWrite;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyContactWrite;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyExternalWrite;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartySupplyWrite;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyUnitWrite;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyWriteRequest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
public class PartyDirectoryService {

    private final CompanyAccessService access;
    private final JdbcPartyRepository parties;
    private final Clock clock;

    public PartyDirectoryService(CompanyAccessService access, JdbcPartyRepository parties, Clock clock) {
        this.access = access;
        this.parties = parties;
        this.clock = clock;
    }

    public PartyPage list(
            ApplicationPrincipal principal,
            UUID companyId,
            String q,
            String relation,
            String status,
            Boolean documentPending,
            String origin,
            int page,
            int size) {
        AuthorizedScope scope = readable(principal, companyId);
        int safePage = Math.max(page, 0);
        int safeSize = size <= 0 ? 20 : Math.min(size, 50);
        boolean reveal = canRevealDocument(principal, companyId);
        var query = parties.list(scope, q, relation, status, documentPending, origin, safePage, safeSize);
        List<PartyListItem> items = query.items().stream()
                .map(item -> new PartyListItem(
                        item.id(),
                        item.code(),
                        item.name(),
                        item.tradeName(),
                        item.role(),
                        item.active(),
                        item.documentPending(),
                        item.documentType(),
                        item.documentCountry(),
                        DocumentNumbers.mask(item.documentDisplay(), reveal),
                        item.locality(),
                        item.originKind(),
                        item.version()))
                .toList();
        return new PartyPage(items, query.total(), safePage, safeSize);
    }

    public PartyDetail get(ApplicationPrincipal principal, UUID companyId, UUID id) {
        AuthorizedScope scope = readable(principal, companyId);
        PartyRow row = parties.find(scope, id).orElseThrow(() -> new SecurityException("catalog-hidden"));
        return detail(principal, companyId, scope, row);
    }

    public List<PartyCandidate> candidates(
            ApplicationPrincipal principal,
            UUID companyId,
            String name,
            String documentCountry,
            String documentType,
            String documentNumber,
            UUID exceptId) {
        AuthorizedScope scope = readable(principal, companyId);
        boolean reveal = canRevealDocument(principal, companyId);
        List<PartyCandidate> found = new ArrayList<>();
        NormalizedDocument document = DocumentNumbers.parse(documentCountry, documentType, documentNumber);
        if (document != null) {
            parties.findByDocument(scope, document.country(), document.type(), document.normalized(), exceptId)
                    .ifPresent(row -> found.add(candidate(row, "DOCUMENT", reveal)));
            parties.findUnitOwnerByDocument(scope, document.country(), document.type(), document.normalized())
                    .flatMap(id -> parties.find(scope, id))
                    .filter(row -> exceptId == null || !row.id().equals(exceptId))
                    .ifPresent(row -> {
                        if (found.stream().noneMatch(item -> item.id().equals(row.id()))) {
                            found.add(candidate(row, "UNIT_DOCUMENT", reveal));
                        }
                    });
        }
        if (name != null && !name.isBlank()) {
            for (PartyCandidate item : parties.findNameCandidates(scope, name, exceptId)) {
                if (found.stream().noneMatch(existing -> existing.id().equals(item.id()))) {
                    found.add(new PartyCandidate(
                            item.id(),
                            item.name(),
                            item.tradeName(),
                            item.role(),
                            item.active(),
                            DocumentNumbers.mask(item.documentDisplay(), reveal),
                            item.matchKind()));
                }
            }
        }
        return found;
    }

    @Transactional
    public PartyDetail create(ApplicationPrincipal principal, UUID companyId, PartyWriteRequest body) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
        Instant now = Instant.now(clock);
        Draft draft = validate(scope, body, null);
        UUID id = UUID.randomUUID();
        PartyRow row = new PartyRow(
                id,
                scope.tenantId(),
                scope.companyId(),
                "CTP-" + id,
                draft.name(),
                draft.tradeName(),
                draft.personKind(),
                draft.role(),
                draft.active(),
                draft.document() == null,
                draft.document() == null ? null : draft.document().country(),
                draft.document() == null ? null : draft.document().type(),
                draft.document() == null ? null : draft.document().display(),
                draft.document() == null ? null : draft.document().normalized(),
                draft.originKind(),
                draft.notes(),
                1L,
                now,
                now,
                principal.actorId(),
                principal.actorId());
        try {
            parties.insertParty(row, principal.actorId());
        } catch (DataIntegrityViolationException ex) {
            throw new CatalogConflictException("Já existe um cadastro com este documento nesta empresa.");
        }
        persistChildren(scope, id, draft, now, principal.actorId());
        parties.insertHistory(
                scope, id, 1L, "CREATED", principal.actorId(), clip(principal.displayName()), now, null, null);
        return get(principal, companyId, id);
    }

    @Transactional
    public PartyDetail update(ApplicationPrincipal principal, UUID companyId, UUID id, PartyWriteRequest body) {
        if (body == null || body.version() == null) {
            throw ValidationException.of("version", "Versão é obrigatória.");
        }
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
        PartyRow current = parties.lock(scope, id).orElseThrow(() -> new SecurityException("catalog-hidden"));
        if (current.version() != body.version()) {
            throw new VersionConflictException("Este cadastro foi alterado por outra pessoa.");
        }
        Instant now = Instant.now(clock);
        Draft draft = validate(scope, body, id);
        boolean wasActive = current.active();
        PartyRow row = new PartyRow(
                id,
                scope.tenantId(),
                scope.companyId(),
                current.code(),
                draft.name(),
                draft.tradeName(),
                draft.personKind(),
                draft.role(),
                draft.active(),
                draft.document() == null,
                draft.document() == null ? null : draft.document().country(),
                draft.document() == null ? null : draft.document().type(),
                draft.document() == null ? null : draft.document().display(),
                draft.document() == null ? null : draft.document().normalized(),
                current.originKind(),
                draft.notes(),
                current.version(),
                current.createdAt(),
                now,
                current.createdBy(),
                principal.actorId());
        try {
            if (parties.updateParty(row, current.version(), now, principal.actorId()) != 1) {
                throw new VersionConflictException("Este cadastro foi alterado por outra pessoa.");
            }
        } catch (DataIntegrityViolationException ex) {
            throw new CatalogConflictException("Já existe um cadastro com este documento nesta empresa.");
        }
        persistChildren(scope, id, draft, now, principal.actorId());
        String action = "UPDATED";
        if (wasActive && !draft.active()) {
            action = "INACTIVATED";
        } else if (!wasActive && draft.active()) {
            action = "REACTIVATED";
        }
        parties.insertHistory(
                scope,
                id,
                current.version() + 1,
                action,
                principal.actorId(),
                clip(principal.displayName()),
                now,
                null,
                null);
        return get(principal, companyId, id);
    }

    private void persistChildren(AuthorizedScope scope, UUID partyId, Draft draft, Instant now, UUID actorId) {
        parties.deactivateAllUnits(scope, partyId, now, actorId);
        for (UnitRow unit : draft.units()) {
            parties.upsertUnit(scope, partyId, unit, now, actorId);
        }
        parties.deactivateAllAddresses(scope, partyId, now, actorId);
        for (AddressRow address : draft.addresses()) {
            parties.upsertAddress(scope, partyId, address, now, actorId);
        }
        parties.deactivateAllContacts(scope, partyId, now, actorId);
        for (ContactRow contact : draft.contacts()) {
            parties.upsertContact(scope, partyId, contact, now, actorId);
        }
        parties.deactivateAllSupplies(scope, partyId, now, actorId);
        for (SupplyRow supply : draft.supplies()) {
            parties.upsertSupply(scope, partyId, supply, now, actorId);
        }
        for (ExternalRow external : draft.externals()) {
            try {
                parties.insertExternal(scope, partyId, external, now, actorId);
            } catch (DataIntegrityViolationException ex) {
                throw new CatalogConflictException(
                        "Esta identidade externa já está vinculada a um cadastro desta empresa.");
            }
        }
        try {
            parties.replaceClaims(
                    scope,
                    partyId,
                    draft.document() == null ? null : draft.document().country(),
                    draft.document() == null ? null : draft.document().type(),
                    draft.document() == null ? null : draft.document().normalized(),
                    now);
        } catch (DataIntegrityViolationException ex) {
            throw new CatalogConflictException("Este documento já identifica outro cadastro nesta empresa.");
        }
    }

    private Draft validate(AuthorizedScope scope, PartyWriteRequest body, UUID exceptId) {
        if (body == null) {
            throw ValidationException.of("name", "Nome é obrigatório.");
        }
        Map<String, String> errors = new LinkedHashMap<>();
        String name = trimToNull(body.name());
        if (name == null || name.length() > 160) {
            errors.put("name", "Nome é obrigatório e deve ter até 160 caracteres.");
        }
        CounterpartyRole role = resolveRole(body, errors);
        PersonKind personKind = parsePerson(body.personKind(), errors);
        String tradeName = trimToNull(body.tradeName());
        if (tradeName != null && tradeName.length() > 160) {
            errors.put("tradeName", "Nome fantasia deve ter até 160 caracteres.");
        }
        NormalizedDocument document = null;
        try {
            document = DocumentNumbers.parse(
                    body.documentCountry(), body.documentType(), body.documentNumber(), personKind);
        } catch (ValidationException ex) {
            errors.putAll(ex.fields());
        }
        if (document != null) {
            parties.findDocumentClaimOwner(
                            scope, document.country(), document.type(), document.normalized(), exceptId)
                    .ifPresent(existing -> {
                        throw new CatalogConflictException(
                                "Este documento já identifica outro cadastro nesta empresa.");
                    });
        }
        OriginKind origin = OriginKind.MANUAL;
        if (body.originKind() != null && !body.originKind().isBlank()) {
            try {
                origin = OriginKind.valueOf(body.originKind());
            } catch (IllegalArgumentException ex) {
                errors.put("originKind", "Origem não reconhecida.");
            }
        }
        String notes = trimToNull(body.notes());
        if (notes != null && notes.length() > 500) {
            errors.put("notes", "Observação deve ter até 500 caracteres.");
        }
        boolean active = body.active() == null || body.active();
        List<UnitRow> units = new ArrayList<>();
        if (body.units() != null) {
            for (PartyUnitWrite unit : body.units()) {
                units.add(validateUnit(scope, exceptId, document, personKind, unit, errors, units.size()));
            }
        }
        List<UUID> draftUnitIds = units.stream().map(UnitRow::id).toList();
        List<AddressRow> addresses = new ArrayList<>();
        if (body.addresses() != null) {
            for (PartyAddressWrite address : body.addresses()) {
                addresses.add(validateAddress(scope, exceptId, draftUnitIds, address, errors, addresses.size()));
            }
        }
        List<ContactRow> contacts = new ArrayList<>();
        if (body.contacts() != null) {
            for (PartyContactWrite contact : body.contacts()) {
                contacts.add(validateContact(contact, errors, contacts.size()));
            }
        }
        List<SupplyRow> supplies = new ArrayList<>();
        if (body.supplies() != null) {
            for (PartySupplyWrite supply : body.supplies()) {
                supplies.add(validateSupply(supply, errors, supplies.size()));
            }
        }
        List<ExternalRow> externals = new ArrayList<>();
        if (body.externalIdentities() != null) {
            for (PartyExternalWrite external : body.externalIdentities()) {
                externals.add(validateExternal(external, errors, externals.size()));
            }
        }
        long primaries = units.stream().filter(UnitRow::primary).count();
        if (primaries > 1) {
            errors.put("units", "Informe só uma unidade principal.");
        }
        if (!errors.isEmpty()) {
            throw new ValidationException("Revise os campos destacados.", errors);
        }
        return new Draft(name, tradeName, personKind, role, active, document, origin, notes, units, addresses, contacts, supplies, externals);
    }

    private UnitRow validateUnit(
            AuthorizedScope scope,
            UUID exceptId,
            NormalizedDocument personDocument,
            PersonKind personKind,
            PartyUnitWrite unit,
            Map<String, String> errors,
            int index) {
        String prefix = "units[" + index + "]";
        String name = unit == null ? null : trimToNull(unit.name());
        if (name == null) {
            errors.put(prefix + ".name", "Informe o nome da unidade.");
        }
        UnitKind kind = UnitKind.OTHER;
        try {
            kind = UnitKind.valueOf(unit == null || unit.unitKind() == null ? "OTHER" : unit.unitKind());
        } catch (IllegalArgumentException ex) {
            errors.put(prefix + ".unitKind", "Tipo de unidade não reconhecido.");
        }
        NormalizedDocument document = null;
        try {
            document = unit == null
                    ? null
                    : DocumentNumbers.parse(
                            unit.documentCountry(), unit.documentType(), unit.documentNumber(), personKind);
        } catch (ValidationException ex) {
            ex.fields().forEach((key, value) -> errors.put(prefix + "." + key, value));
        }
        boolean primary = unit != null && Boolean.TRUE.equals(unit.primary());
        if (sameIdentity(document, personDocument)) {
            if (!primary) {
                errors.put(prefix + ".documentNumber", "O documento da matriz só pode ser espelhado na unidade principal da mesma pessoa.");
            }
        } else if (document != null) {
            parties.findDocumentClaimOwner(scope, document.country(), document.type(), document.normalized(), exceptId)
                    .ifPresent(owner -> errors.put(
                            prefix + ".documentNumber",
                            "Este documento já identifica outro cadastro nesta empresa."));
        }
        return new UnitRow(
                unit != null && unit.id() != null ? unit.id() : UUID.randomUUID(),
                null,
                name == null ? "" : name,
                kind,
                primary,
                unit == null || unit.active() == null || unit.active(),
                document == null ? null : document.country(),
                document == null ? null : document.type(),
                document == null ? null : document.display(),
                document == null ? null : document.normalized());
    }

    private AddressRow validateAddress(
            AuthorizedScope scope,
            UUID partyId,
            List<UUID> draftUnitIds,
            PartyAddressWrite address,
            Map<String, String> errors,
            int index) {
        String prefix = "addresses[" + index + "]";
        String country = address == null || trimToNull(address.country()) == null ? "BR" : address.country().trim().toUpperCase();
        if (country.length() != 2) {
            errors.put(prefix + ".country", "País deve ter duas letras.");
        }
        boolean noNumber = address != null && Boolean.TRUE.equals(address.noNumber());
        String number = address == null ? null : trimToNull(address.number());
        if (noNumber) {
            number = null;
        }
        String street = address == null ? null : trimToNull(address.street());
        String postal = address == null ? null : trimToNull(address.postalCode());
        String district = address == null ? null : trimToNull(address.district());
        String municipality = address == null ? null : trimToNull(address.municipality());
        String region = address == null ? null : trimToNull(address.region());
        String complement = address == null ? null : trimToNull(address.complement());
        boolean incomplete = street == null || municipality == null || region == null || postal == null || (number == null && !noNumber);
        UUID unitId = address == null ? null : address.unitId();
        if (unitId != null && !draftUnitIds.contains(unitId)) {
            Optional<UUID> owner = parties.findUnit(scope, unitId);
            if (owner.isEmpty() || partyId == null || !owner.get().equals(partyId)) {
                errors.put(prefix + ".unitId", "A unidade do endereço deve pertencer a este cadastro.");
            }
        }
        AddressUsage usage = AddressUsage.MAIN;
        try {
            usage = AddressUsage.valueOf(address == null || address.usage() == null ? "MAIN" : address.usage());
        } catch (IllegalArgumentException ex) {
            errors.put(prefix + ".usage", "Uso do endereço não reconhecido.");
        }
        return new AddressRow(
                address != null && address.id() != null ? address.id() : UUID.randomUUID(),
                null,
                address == null ? null : address.unitId(),
                country,
                postal,
                street,
                number,
                noNumber,
                complement,
                district,
                municipality,
                region,
                usage,
                incomplete,
                address == null || address.active() == null || address.active());
    }

    private ContactRow validateContact(PartyContactWrite contact, Map<String, String> errors, int index) {
        String prefix = "contacts[" + index + "]";
        String name = contact == null ? null : trimToNull(contact.name());
        if (name == null) {
            errors.put(prefix + ".name", "Informe o nome do contato.");
        }
        String email = contact == null ? null : trimToNull(contact.email());
        if (email != null && (email.length() > 254 || !email.contains("@"))) {
            errors.put(prefix + ".email", "E-mail inválido.");
        }
        return new ContactRow(
                contact != null && contact.id() != null ? contact.id() : UUID.randomUUID(),
                null,
                name == null ? "" : name,
                contact == null ? null : trimToNull(contact.roleTitle()),
                email,
                contact == null ? null : trimToNull(contact.phone()),
                contact != null && Boolean.TRUE.equals(contact.primary()),
                contact == null || contact.active() == null || contact.active());
    }

    private SupplyRow validateSupply(PartySupplyWrite supply, Map<String, String> errors, int index) {
        String prefix = "supplies[" + index + "]";
        String description = supply == null ? null : trimToNull(supply.description());
        if (description == null) {
            errors.put(prefix + ".description", "Informe o produto ou serviço fornecido.");
        }
        return new SupplyRow(
                supply != null && supply.id() != null ? supply.id() : UUID.randomUUID(),
                null,
                description == null ? "" : description,
                supply == null ? null : trimToNull(supply.supplyCategory()),
                supply == null ? null : trimToNull(supply.notes()),
                supply == null || supply.active() == null || supply.active());
    }

    private ExternalRow validateExternal(PartyExternalWrite external, Map<String, String> errors, int index) {
        String prefix = "externalIdentities[" + index + "]";
        String system = external == null ? null : trimToNull(external.originSystem());
        String extId = external == null ? null : trimToNull(external.externalId());
        if (system == null || extId == null) {
            errors.put(prefix, "Identidade externa exige sistema e ID na origem.");
        }
        return new ExternalRow(
                UUID.randomUUID(),
                null,
                system == null ? "OTHER" : system,
                external == null || trimToNull(external.connectionKey()) == null
                        ? ""
                        : trimToNull(external.connectionKey()),
                extId == null ? "" : extId,
                external == null ? null : external.observedAt());
    }

    private static CounterpartyRole resolveRole(PartyWriteRequest body, Map<String, String> errors) {
        boolean customer = Boolean.TRUE.equals(body.customer())
                || "CUSTOMER".equalsIgnoreCase(body.role())
                || "BOTH".equalsIgnoreCase(body.role());
        boolean supplier = Boolean.TRUE.equals(body.supplier())
                || "SUPPLIER".equalsIgnoreCase(body.role())
                || "BOTH".equalsIgnoreCase(body.role());
        if (!customer && !supplier && body.role() != null) {
            try {
                return CounterpartyRole.valueOf(body.role());
            } catch (IllegalArgumentException ex) {
                errors.put("role", "Informe se o cadastro é cliente, fornecedor ou ambos.");
                return CounterpartyRole.CUSTOMER;
            }
        }
        if (customer && supplier) {
            return CounterpartyRole.BOTH;
        }
        if (customer) {
            return CounterpartyRole.CUSTOMER;
        }
        if (supplier) {
            return CounterpartyRole.SUPPLIER;
        }
        errors.put("role", "Informe se o cadastro é cliente, fornecedor ou ambos.");
        return CounterpartyRole.CUSTOMER;
    }

    private static boolean sameIdentity(NormalizedDocument left, NormalizedDocument right) {
        return left != null
                && right != null
                && left.country().equals(right.country())
                && left.type() == right.type()
                && left.normalized().equals(right.normalized());
    }

    private static PersonKind parsePerson(String raw, Map<String, String> errors) {
        if (raw == null || raw.isBlank()) {
            return PersonKind.UNSPECIFIED;
        }
        try {
            return PersonKind.valueOf(raw);
        } catch (IllegalArgumentException ex) {
            errors.put("personKind", "Tipo de pessoa não reconhecido.");
            return PersonKind.UNSPECIFIED;
        }
    }

    private PartyDetail detail(ApplicationPrincipal principal, UUID companyId, AuthorizedScope scope, PartyRow row) {
        boolean reveal = canRevealDocument(principal, companyId);
        boolean referenced = parties.hasTitles(scope, row.id());
        var units = parties.listUnits(scope, row.id(), reveal);
        var addresses = parties.listAddresses(scope, row.id());
        var contacts = parties.listContacts(scope, row.id());
        var supplies = parties.listSupplies(scope, row.id());
        var externals = parties.listExternals(scope, row.id());
        var history = parties.listHistory(scope, row.id());
        boolean addressReady = addresses.stream().anyMatch(item -> item.active() && !item.incomplete());
        boolean contactReady = contacts.stream().anyMatch(item -> item.active() && item.email() != null);
        PartyCompleteness completeness = new PartyCompleteness(
                true,
                !row.documentPending(),
                addressReady,
                contactReady,
                false,
                "Cadastro mínimo não autoriza pagamento. Beneficiário exige jornada própria.");
        return parties.toDetail(row, reveal, referenced, completeness, units, addresses, contacts, supplies, externals, history);
    }

    private PartyCandidate candidate(PartyRow row, String kind, boolean reveal) {
        return new PartyCandidate(
                row.id(),
                row.name(),
                row.tradeName(),
                row.role(),
                row.active(),
                DocumentNumbers.mask(row.documentNormalized(), reveal),
                kind);
    }

    private AuthorizedScope readable(ApplicationPrincipal principal, UUID companyId) {
        CompanyView company = access.requireReadable(principal, companyId);
        access.requirePermission(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_READ);
        return new AuthorizedScope(company.tenantId(), company.id());
    }

    private static boolean canRevealDocument(ApplicationPrincipal principal, UUID companyId) {
        return principal.hasPermission(companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
    }

    private static String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private static String clip(String name) {
        if (name == null || name.isBlank()) {
            return null;
        }
        return name.length() > 160 ? name.substring(0, 160) : name;
    }

    private record Draft(
            String name,
            String tradeName,
            PersonKind personKind,
            CounterpartyRole role,
            boolean active,
            NormalizedDocument document,
            OriginKind originKind,
            String notes,
            List<UnitRow> units,
            List<AddressRow> addresses,
            List<ContactRow> contacts,
            List<SupplyRow> supplies,
            List<ExternalRow> externals) {}
}
