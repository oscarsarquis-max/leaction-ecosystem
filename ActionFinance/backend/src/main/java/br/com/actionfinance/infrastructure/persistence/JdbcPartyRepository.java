package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.PartyRecords.ImportBatchView;
import br.com.actionfinance.application.finance.PartyRecords.ImportLineView;
import br.com.actionfinance.application.finance.PartyRecords.ImportReport;
import br.com.actionfinance.application.finance.PartyRecords.PartyAddressView;
import br.com.actionfinance.application.finance.PartyRecords.PartyCandidate;
import br.com.actionfinance.application.finance.PartyRecords.PartyContactView;
import br.com.actionfinance.application.finance.PartyRecords.PartyDetail;
import br.com.actionfinance.application.finance.PartyRecords.PartyExternalView;
import br.com.actionfinance.application.finance.PartyRecords.PartyHistoryView;
import br.com.actionfinance.application.finance.PartyRecords.PartyListItem;
import br.com.actionfinance.application.finance.PartyRecords.PartySupplyView;
import br.com.actionfinance.application.finance.PartyRecords.PartyUnitView;
import br.com.actionfinance.domain.AddressUsage;
import br.com.actionfinance.domain.CounterpartyRole;
import br.com.actionfinance.domain.DocumentNumbers;
import br.com.actionfinance.domain.DocumentType;
import br.com.actionfinance.domain.OriginKind;
import br.com.actionfinance.domain.PersonKind;
import br.com.actionfinance.domain.UnitKind;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcPartyRepository {

    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;

    public JdbcPartyRepository(JdbcTemplate jdbc, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    public record PartyRow(
            UUID id,
            UUID tenantId,
            UUID companyId,
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
            String documentNormalized,
            OriginKind originKind,
            String notes,
            long version,
            Instant createdAt,
            Instant updatedAt,
            UUID createdBy,
            UUID updatedBy) {}

    public record UnitRow(
            UUID id,
            UUID counterpartyId,
            String name,
            UnitKind unitKind,
            boolean primary,
            boolean active,
            String documentCountry,
            DocumentType documentType,
            String documentNumber,
            String documentNormalized) {}

    public record AddressRow(
            UUID id,
            UUID counterpartyId,
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

    public record ContactRow(
            UUID id,
            UUID counterpartyId,
            String name,
            String roleTitle,
            String email,
            String phone,
            boolean primary,
            boolean active) {}

    public record SupplyRow(
            UUID id, UUID counterpartyId, String description, String supplyCategory, String notes, boolean active) {}

    public record ExternalRow(
            UUID id,
            UUID counterpartyId,
            String originSystem,
            String connectionKey,
            String externalId,
            Instant observedAt) {}

    public record ImportBatchRow(
            UUID id,
            String filename,
            String contentSha,
            String status,
            int totalLines,
            Map<String, String> columnMap,
            Instant createdAt) {}

    public record ImportLineRow(
            UUID id,
            UUID batchId,
            int lineNo,
            Map<String, String> raw,
            String classification,
            boolean selected,
            UUID matchId,
            Long previewVersion,
            String result,
            String errorMessage,
            String idempotencyKey) {}

    private static final RowMapper<PartyRow> PARTY = (rs, rowNum) -> new PartyRow(
            rs.getObject("id", UUID.class),
            rs.getObject("tenant_id", UUID.class),
            rs.getObject("company_id", UUID.class),
            rs.getString("code"),
            rs.getString("name"),
            rs.getString("trade_name"),
            PersonKind.valueOf(rs.getString("person_kind")),
            CounterpartyRole.valueOf(rs.getString("role")),
            rs.getBoolean("active"),
            rs.getBoolean("document_pending"),
            rs.getString("document_country"),
            optionalType(rs.getString("document_type")),
            rs.getString("document_number"),
            rs.getString("document_number_normalized"),
            OriginKind.valueOf(rs.getString("origin_kind")),
            rs.getString("notes"),
            rs.getLong("version"),
            rs.getTimestamp("created_at").toInstant(),
            rs.getTimestamp("updated_at").toInstant(),
            rs.getObject("created_by", UUID.class),
            rs.getObject("updated_by", UUID.class));

    public PartyPageQuery list(
            AuthorizedScope scope,
            String q,
            String relation,
            String status,
            Boolean documentPending,
            String origin,
            int page,
            int size) {
        StringBuilder where = new StringBuilder(" where c.tenant_id = ? and c.company_id = ? ");
        List<Object> args = new ArrayList<>();
        args.add(scope.tenantId());
        args.add(scope.companyId());
        if (q != null && !q.isBlank()) {
            String like = "%" + q.trim() + "%";
            String compact = DocumentNumbers.normalizeToken(q);
            where.append(
                    """
                    and (
                        c.name ilike ?
                        or coalesce(c.trade_name,'') ilike ?
                        or coalesce(c.document_number,'') ilike ?
                        or coalesce(c.document_number_normalized,'') = ?
                        or exists (
                            select 1 from actionfinance.counterparty_external_identity x
                            where x.tenant_id = c.tenant_id and x.company_id = c.company_id
                              and x.counterparty_id = c.id and x.external_id ilike ?
                        )
                    )
                    """);
            args.add(like);
            args.add(like);
            args.add(like);
            args.add(compact == null ? "" : compact);
            args.add(like);
        }
        if ("CUSTOMER".equals(relation)) {
            where.append(" and c.role in ('CUSTOMER','BOTH') ");
        } else if ("SUPPLIER".equals(relation)) {
            where.append(" and c.role in ('SUPPLIER','BOTH') ");
        } else if ("BOTH".equals(relation)) {
            where.append(" and c.role = 'BOTH' ");
        }
        if ("ACTIVE".equals(status)) {
            where.append(" and c.active = true ");
        } else if ("INACTIVE".equals(status)) {
            where.append(" and c.active = false ");
        }
        if (documentPending != null) {
            where.append(" and c.document_pending = ? ");
            args.add(documentPending);
        }
        if (origin != null && !origin.isBlank() && !"ALL".equals(origin)) {
            where.append(" and c.origin_kind = ? ");
            args.add(origin);
        }
        Long total = jdbc.queryForObject(
                "select count(*) from actionfinance.counterparty c" + where,
                Long.class,
                args.toArray());
        int offset = page * size;
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(size);
        pageArgs.add(offset);
        List<PartyListItem> items = jdbc.query(
                """
                select c.*,
                    (
                        select trim(both ', ' from concat_ws(', ', a.municipality, a.region))
                        from actionfinance.counterparty_address a
                        where a.tenant_id = c.tenant_id and a.company_id = c.company_id
                          and a.counterparty_id = c.id and a.active
                        order by case when a.usage = 'MAIN' then 0 else 1 end, a.id
                        limit 1
                    ) as locality
                from actionfinance.counterparty c
                """
                        + where
                        + " order by c.name, c.id limit ? offset ?",
                (rs, rowNum) -> new PartyListItem(
                        rs.getObject("id", UUID.class),
                        rs.getString("code"),
                        rs.getString("name"),
                        rs.getString("trade_name"),
                        CounterpartyRole.valueOf(rs.getString("role")),
                        rs.getBoolean("active"),
                        rs.getBoolean("document_pending"),
                        rs.getString("document_type"),
                        rs.getString("document_country"),
                        rs.getString("document_number_normalized"),
                        rs.getString("locality"),
                        OriginKind.valueOf(rs.getString("origin_kind")),
                        rs.getLong("version")),
                pageArgs.toArray());
        return new PartyPageQuery(items, total == null ? 0 : total);
    }

    public record PartyPageQuery(List<PartyListItem> items, long total) {}

    public Optional<PartyRow> find(AuthorizedScope scope, UUID id) {
        return jdbc
                .query(
                        """
                        select * from actionfinance.counterparty
                        where tenant_id = ? and company_id = ? and id = ?
                        """,
                        PARTY,
                        scope.tenantId(),
                        scope.companyId(),
                        id)
                .stream()
                .findFirst();
    }

    public Optional<PartyRow> lock(AuthorizedScope scope, UUID id) {
        return jdbc
                .query(
                        """
                        select * from actionfinance.counterparty
                        where tenant_id = ? and company_id = ? and id = ?
                        for update
                        """,
                        PARTY,
                        scope.tenantId(),
                        scope.companyId(),
                        id)
                .stream()
                .findFirst();
    }

    public Optional<PartyRow> findByDocument(
            AuthorizedScope scope, String country, DocumentType type, String normalized, UUID exceptId) {
        List<PartyRow> rows = jdbc.query(
                """
                select * from actionfinance.counterparty
                where tenant_id = ? and company_id = ?
                  and document_country = ? and document_type = ? and document_number_normalized = ?
                  and (?::uuid is null or id <> ?)
                """,
                PARTY,
                scope.tenantId(),
                scope.companyId(),
                country,
                type.name(),
                normalized,
                exceptId,
                exceptId);
        return rows.stream().findFirst();
    }

    public Optional<UUID> findDocumentClaimOwner(
            AuthorizedScope scope, String country, DocumentType type, String normalized, UUID exceptPartyId) {
        List<UUID> ids = jdbc.query(
                """
                select counterparty_id from actionfinance.counterparty_document_claim
                where tenant_id = ? and company_id = ?
                  and document_country = ? and document_type = ? and document_number_normalized = ?
                  and (?::uuid is null or counterparty_id <> ?)
                """,
                (rs, rowNum) -> rs.getObject("counterparty_id", UUID.class),
                scope.tenantId(),
                scope.companyId(),
                country,
                type.name(),
                normalized,
                exceptPartyId,
                exceptPartyId);
        return ids.stream().findFirst();
    }

    public Optional<UUID> findUnit(AuthorizedScope scope, UUID unitId) {
        List<UUID> ids = jdbc.query(
                """
                select counterparty_id from actionfinance.counterparty_unit
                where tenant_id = ? and company_id = ? and id = ?
                """,
                (rs, rowNum) -> rs.getObject("counterparty_id", UUID.class),
                scope.tenantId(),
                scope.companyId(),
                unitId);
        return ids.stream().findFirst();
    }

    public void replaceClaims(
            AuthorizedScope scope,
            UUID partyId,
            String personCountry,
            DocumentType personType,
            String personNormalized,
            Instant now) {
        jdbc.update(
                """
                delete from actionfinance.counterparty_document_claim
                where tenant_id = ? and company_id = ? and counterparty_id = ?
                """,
                scope.tenantId(),
                scope.companyId(),
                partyId);
        if (personNormalized != null) {
            jdbc.update(
                    """
                    insert into actionfinance.counterparty_document_claim (
                        tenant_id, company_id, document_country, document_type, document_number_normalized,
                        counterparty_id, unit_id, mirrored, created_at)
                    values (?,?,?,?,?,?,null,false,?)
                    """,
                    scope.tenantId(),
                    scope.companyId(),
                    personCountry,
                    personType.name(),
                    personNormalized,
                    partyId,
                    Timestamp.from(now));
        }
        List<UnitRow> stored = jdbc.query(
                """
                select id, counterparty_id, name, unit_kind, is_primary, active,
                       document_country, document_type, document_number, document_number_normalized
                  from actionfinance.counterparty_unit
                 where tenant_id = ? and company_id = ? and counterparty_id = ?
                """,
                (rs, rowNum) -> new UnitRow(
                        rs.getObject("id", UUID.class),
                        rs.getObject("counterparty_id", UUID.class),
                        rs.getString("name"),
                        UnitKind.valueOf(rs.getString("unit_kind")),
                        rs.getBoolean("is_primary"),
                        rs.getBoolean("active"),
                        rs.getString("document_country"),
                        optionalType(rs.getString("document_type")),
                        rs.getString("document_number"),
                        rs.getString("document_number_normalized")),
                scope.tenantId(),
                scope.companyId(),
                partyId);
        for (UnitRow unit : stored) {
            if (unit.documentNormalized() == null) {
                continue;
            }
            boolean mirror = personNormalized != null
                    && personCountry != null
                    && personType != null
                    && personCountry.equals(unit.documentCountry())
                    && personType == unit.documentType()
                    && personNormalized.equals(unit.documentNormalized())
                    && unit.primary();
            if (mirror) {
                int updated = jdbc.update(
                        """
                        update actionfinance.counterparty_document_claim
                           set unit_id = ?, mirrored = true
                         where tenant_id = ? and company_id = ?
                           and document_country = ? and document_type = ?
                           and document_number_normalized = ? and counterparty_id = ?
                           and mirrored = false
                           and unit_id is null
                        """,
                        unit.id(),
                        scope.tenantId(),
                        scope.companyId(),
                        personCountry,
                        personType.name(),
                        personNormalized,
                        partyId);
                if (updated != 1) {
                    throw ValidationException.of(
                            "units",
                            "Não foi possível registrar o espelho deste documento na unidade principal.");
                }
                continue;
            }
            jdbc.update(
                    """
                    insert into actionfinance.counterparty_document_claim (
                        tenant_id, company_id, document_country, document_type, document_number_normalized,
                        counterparty_id, unit_id, mirrored, created_at)
                    values (?,?,?,?,?,?,?,?,?)
                    """,
                    scope.tenantId(),
                    scope.companyId(),
                    unit.documentCountry(),
                    unit.documentType().name(),
                    unit.documentNormalized(),
                    partyId,
                    unit.id(),
                    false,
                    Timestamp.from(now));
        }
    }

    public Optional<UUID> findUnitOwnerByDocument(
            AuthorizedScope scope, String country, DocumentType type, String normalized) {
        List<UUID> ids = jdbc.query(
                """
                select counterparty_id from actionfinance.counterparty_unit
                where tenant_id = ? and company_id = ?
                  and document_country = ? and document_type = ? and document_number_normalized = ?
                  and active
                """,
                (rs, rowNum) -> rs.getObject("counterparty_id", UUID.class),
                scope.tenantId(),
                scope.companyId(),
                country,
                type.name(),
                normalized);
        return ids.stream().findFirst();
    }

    public List<PartyCandidate> findNameCandidates(AuthorizedScope scope, String name, UUID exceptId) {
        String like = name.trim();
        return jdbc.query(
                """
                select id, name, trade_name, role, active, document_number_normalized
                from actionfinance.counterparty
                where tenant_id = ? and company_id = ?
                  and (?::uuid is null or id <> ?)
                  and (lower(name) = lower(?) or lower(coalesce(trade_name,'')) = lower(?))
                order by name, id
                limit 8
                """,
                (rs, rowNum) -> new PartyCandidate(
                        rs.getObject("id", UUID.class),
                        rs.getString("name"),
                        rs.getString("trade_name"),
                        CounterpartyRole.valueOf(rs.getString("role")),
                        rs.getBoolean("active"),
                        rs.getString("document_number_normalized"),
                        "NAME"),
                scope.tenantId(),
                scope.companyId(),
                exceptId,
                exceptId,
                like,
                like);
    }

    public void insertParty(PartyRow row, UUID actorId) {
        jdbc.update(
                """
                insert into actionfinance.counterparty (
                    id, tenant_id, company_id, code, name, trade_name, person_kind, role, active,
                    document_country, document_type, document_number, document_number_normalized,
                    document_pending, origin_kind, notes, version,
                    created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                row.id(),
                row.tenantId(),
                row.companyId(),
                row.code(),
                row.name(),
                row.tradeName(),
                row.personKind().name(),
                row.role().name(),
                row.active(),
                row.documentCountry(),
                row.documentType() == null ? null : row.documentType().name(),
                row.documentNumber(),
                row.documentNormalized(),
                row.documentPending(),
                row.originKind().name(),
                row.notes(),
                row.version(),
                Timestamp.from(row.createdAt()),
                Timestamp.from(row.updatedAt()),
                actorId,
                actorId);
    }

    public int updateParty(PartyRow row, long expectedVersion, Instant now, UUID actorId) {
        return jdbc.update(
                """
                update actionfinance.counterparty
                set name = ?,
                    trade_name = ?,
                    person_kind = ?,
                    role = ?,
                    active = ?,
                    document_country = ?,
                    document_type = ?,
                    document_number = ?,
                    document_number_normalized = ?,
                    document_pending = ?,
                    origin_kind = ?,
                    notes = ?,
                    version = version + 1,
                    updated_at = ?,
                    updated_by = ?
                where tenant_id = ? and company_id = ? and id = ? and version = ?
                """,
                row.name(),
                row.tradeName(),
                row.personKind().name(),
                row.role().name(),
                row.active(),
                row.documentCountry(),
                row.documentType() == null ? null : row.documentType().name(),
                row.documentNumber(),
                row.documentNormalized(),
                row.documentPending(),
                row.originKind().name(),
                row.notes(),
                Timestamp.from(now),
                actorId,
                row.tenantId(),
                row.companyId(),
                row.id(),
                expectedVersion);
    }

    public boolean hasTitles(AuthorizedScope scope, UUID id) {
        Integer count = jdbc.queryForObject(
                """
                select count(*) from actionfinance.financial_title
                where tenant_id = ? and company_id = ? and counterparty_id = ?
                """,
                Integer.class,
                scope.tenantId(),
                scope.companyId(),
                id);
        return count != null && count > 0;
    }

    public List<PartyUnitView> listUnits(AuthorizedScope scope, UUID partyId, boolean revealDocument) {
        return jdbc.query(
                """
                select * from actionfinance.counterparty_unit
                where tenant_id = ? and company_id = ? and counterparty_id = ?
                order by is_primary desc, name, id
                """,
                (rs, rowNum) -> new PartyUnitView(
                        rs.getObject("id", UUID.class),
                        rs.getString("name"),
                        UnitKind.valueOf(rs.getString("unit_kind")),
                        rs.getBoolean("is_primary"),
                        rs.getBoolean("active"),
                        rs.getString("document_country"),
                        optionalType(rs.getString("document_type")),
                        revealDocument ? rs.getString("document_number") : null,
                        DocumentNumbers.mask(rs.getString("document_number_normalized"), revealDocument)),
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public List<PartyAddressView> listAddresses(AuthorizedScope scope, UUID partyId) {
        return jdbc.query(
                """
                select * from actionfinance.counterparty_address
                where tenant_id = ? and company_id = ? and counterparty_id = ?
                order by usage, id
                """,
                (rs, rowNum) -> new PartyAddressView(
                        rs.getObject("id", UUID.class),
                        rs.getObject("unit_id", UUID.class),
                        rs.getString("country"),
                        rs.getString("postal_code"),
                        rs.getString("street"),
                        rs.getString("number"),
                        rs.getBoolean("no_number"),
                        rs.getString("complement"),
                        rs.getString("district"),
                        rs.getString("municipality"),
                        rs.getString("region"),
                        AddressUsage.valueOf(rs.getString("usage")),
                        rs.getBoolean("incomplete"),
                        rs.getBoolean("active")),
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public List<PartyContactView> listContacts(AuthorizedScope scope, UUID partyId) {
        return jdbc.query(
                """
                select * from actionfinance.counterparty_contact
                where tenant_id = ? and company_id = ? and counterparty_id = ?
                order by is_primary desc, name, id
                """,
                (rs, rowNum) -> new PartyContactView(
                        rs.getObject("id", UUID.class),
                        rs.getString("name"),
                        rs.getString("role_title"),
                        rs.getString("email"),
                        rs.getString("phone"),
                        rs.getBoolean("is_primary"),
                        rs.getBoolean("active")),
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public List<PartySupplyView> listSupplies(AuthorizedScope scope, UUID partyId) {
        return jdbc.query(
                """
                select * from actionfinance.counterparty_supply
                where tenant_id = ? and company_id = ? and counterparty_id = ?
                order by description, id
                """,
                (rs, rowNum) -> new PartySupplyView(
                        rs.getObject("id", UUID.class),
                        rs.getString("description"),
                        rs.getString("supply_category"),
                        rs.getString("notes"),
                        rs.getBoolean("active")),
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public List<PartyExternalView> listExternals(AuthorizedScope scope, UUID partyId) {
        return jdbc.query(
                """
                select * from actionfinance.counterparty_external_identity
                where tenant_id = ? and company_id = ? and counterparty_id = ?
                order by origin_system, external_id
                """,
                (rs, rowNum) -> new PartyExternalView(
                        rs.getObject("id", UUID.class),
                        rs.getString("origin_system"),
                        rs.getString("connection_key"),
                        rs.getString("external_id"),
                        rs.getTimestamp("observed_at") == null ? null : rs.getTimestamp("observed_at").toInstant()),
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public List<PartyHistoryView> listHistory(AuthorizedScope scope, UUID partyId) {
        return jdbc.query(
                """
                select * from actionfinance.counterparty_history
                where tenant_id = ? and company_id = ? and counterparty_id = ?
                order by occurred_at desc, id desc
                limit 50
                """,
                (rs, rowNum) -> new PartyHistoryView(
                        rs.getObject("id", UUID.class),
                        rs.getLong("counterparty_version"),
                        rs.getString("action"),
                        rs.getObject("actor_id", UUID.class),
                        rs.getString("actor_display_name"),
                        rs.getTimestamp("occurred_at").toInstant(),
                        rs.getString("reason")),
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public void insertHistory(
            AuthorizedScope scope,
            UUID partyId,
            long version,
            String action,
            UUID actorId,
            String actorName,
            Instant now,
            String reason,
            String changesJson) {
        jdbc.update(
                """
                insert into actionfinance.counterparty_history (
                    id, tenant_id, company_id, counterparty_id, counterparty_version, action,
                    actor_id, actor_display_name, occurred_at, reason, changes)
                values (?,?,?,?,?,?,?,?,?,?,cast(? as jsonb))
                """,
                UUID.randomUUID(),
                scope.tenantId(),
                scope.companyId(),
                partyId,
                version,
                action,
                actorId,
                actorName,
                Timestamp.from(now),
                reason,
                changesJson);
    }

    public void upsertUnit(AuthorizedScope scope, UUID partyId, UnitRow row, Instant now, UUID actorId) {
        int updated = jdbc.update(
                """
                update actionfinance.counterparty_unit
                set name = ?, unit_kind = ?, is_primary = ?, active = ?,
                    document_country = ?, document_type = ?, document_number = ?,
                    document_number_normalized = ?, version = version + 1,
                    updated_at = ?, updated_by = ?
                where tenant_id = ? and company_id = ? and counterparty_id = ? and id = ?
                """,
                row.name(),
                row.unitKind().name(),
                row.primary(),
                row.active(),
                row.documentCountry(),
                row.documentType() == null ? null : row.documentType().name(),
                row.documentNumber(),
                row.documentNormalized(),
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                partyId,
                row.id());
        if (updated == 0) {
            jdbc.update(
                    """
                    insert into actionfinance.counterparty_unit (
                        id, tenant_id, company_id, counterparty_id, name, unit_kind, is_primary, active,
                        document_country, document_type, document_number, document_number_normalized,
                        version, created_at, updated_at, created_by, updated_by)
                    values (?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?)
                    """,
                    row.id(),
                    scope.tenantId(),
                    scope.companyId(),
                    partyId,
                    row.name(),
                    row.unitKind().name(),
                    row.primary(),
                    row.active(),
                    row.documentCountry(),
                    row.documentType() == null ? null : row.documentType().name(),
                    row.documentNumber(),
                    row.documentNormalized(),
                    Timestamp.from(now),
                    Timestamp.from(now),
                    actorId,
                    actorId);
        }
    }

    public void deactivateAllUnits(AuthorizedScope scope, UUID partyId, Instant now, UUID actorId) {
        jdbc.update(
                """
                update actionfinance.counterparty_unit
                set active = false, version = version + 1, updated_at = ?, updated_by = ?
                where tenant_id = ? and company_id = ? and counterparty_id = ? and active = true
                """,
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public void upsertAddress(AuthorizedScope scope, UUID partyId, AddressRow row, Instant now, UUID actorId) {
        int updated = jdbc.update(
                """
                update actionfinance.counterparty_address
                set unit_id = ?, country = ?, postal_code = ?, street = ?, number = ?, no_number = ?,
                    complement = ?, district = ?, municipality = ?, region = ?, usage = ?,
                    incomplete = ?, active = ?, version = version + 1, updated_at = ?, updated_by = ?
                where tenant_id = ? and company_id = ? and counterparty_id = ? and id = ?
                """,
                row.unitId(),
                row.country(),
                row.postalCode(),
                row.street(),
                row.number(),
                row.noNumber(),
                row.complement(),
                row.district(),
                row.municipality(),
                row.region(),
                row.usage().name(),
                row.incomplete(),
                row.active(),
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                partyId,
                row.id());
        if (updated == 0) {
            jdbc.update(
                    """
                    insert into actionfinance.counterparty_address (
                        id, tenant_id, company_id, counterparty_id, unit_id, country, postal_code, street,
                        number, no_number, complement, district, municipality, region, usage, incomplete,
                        active, version, created_at, updated_at, created_by, updated_by)
                    values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?)
                    """,
                    row.id(),
                    scope.tenantId(),
                    scope.companyId(),
                    partyId,
                    row.unitId(),
                    row.country(),
                    row.postalCode(),
                    row.street(),
                    row.number(),
                    row.noNumber(),
                    row.complement(),
                    row.district(),
                    row.municipality(),
                    row.region(),
                    row.usage().name(),
                    row.incomplete(),
                    row.active(),
                    Timestamp.from(now),
                    Timestamp.from(now),
                    actorId,
                    actorId);
        }
    }

    public void deactivateAllAddresses(AuthorizedScope scope, UUID partyId, Instant now, UUID actorId) {
        jdbc.update(
                """
                update actionfinance.counterparty_address
                set active = false, version = version + 1, updated_at = ?, updated_by = ?
                where tenant_id = ? and company_id = ? and counterparty_id = ? and active = true
                """,
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public void upsertContact(AuthorizedScope scope, UUID partyId, ContactRow row, Instant now, UUID actorId) {
        int updated = jdbc.update(
                """
                update actionfinance.counterparty_contact
                set name = ?, role_title = ?, email = ?, phone = ?, is_primary = ?, active = ?,
                    version = version + 1, updated_at = ?, updated_by = ?
                where tenant_id = ? and company_id = ? and counterparty_id = ? and id = ?
                """,
                row.name(),
                row.roleTitle(),
                row.email(),
                row.phone(),
                row.primary(),
                row.active(),
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                partyId,
                row.id());
        if (updated == 0) {
            jdbc.update(
                    """
                    insert into actionfinance.counterparty_contact (
                        id, tenant_id, company_id, counterparty_id, name, role_title, email, phone,
                        is_primary, active, version, created_at, updated_at, created_by, updated_by)
                    values (?,?,?,?,?,?,?,?,?,?,1,?,?,?,?)
                    """,
                    row.id(),
                    scope.tenantId(),
                    scope.companyId(),
                    partyId,
                    row.name(),
                    row.roleTitle(),
                    row.email(),
                    row.phone(),
                    row.primary(),
                    row.active(),
                    Timestamp.from(now),
                    Timestamp.from(now),
                    actorId,
                    actorId);
        }
    }

    public void deactivateAllContacts(AuthorizedScope scope, UUID partyId, Instant now, UUID actorId) {
        jdbc.update(
                """
                update actionfinance.counterparty_contact
                set active = false, version = version + 1, updated_at = ?, updated_by = ?
                where tenant_id = ? and company_id = ? and counterparty_id = ? and active = true
                """,
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public void upsertSupply(AuthorizedScope scope, UUID partyId, SupplyRow row, Instant now, UUID actorId) {
        int updated = jdbc.update(
                """
                update actionfinance.counterparty_supply
                set description = ?, supply_category = ?, notes = ?, active = ?,
                    version = version + 1, updated_at = ?, updated_by = ?
                where tenant_id = ? and company_id = ? and counterparty_id = ? and id = ?
                """,
                row.description(),
                row.supplyCategory(),
                row.notes(),
                row.active(),
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                partyId,
                row.id());
        if (updated == 0) {
            jdbc.update(
                    """
                    insert into actionfinance.counterparty_supply (
                        id, tenant_id, company_id, counterparty_id, description, supply_category, notes,
                        active, version, created_at, updated_at, created_by, updated_by)
                    values (?,?,?,?,?,?,?,?,1,?,?,?,?)
                    """,
                    row.id(),
                    scope.tenantId(),
                    scope.companyId(),
                    partyId,
                    row.description(),
                    row.supplyCategory(),
                    row.notes(),
                    row.active(),
                    Timestamp.from(now),
                    Timestamp.from(now),
                    actorId,
                    actorId);
        }
    }

    public void deactivateAllSupplies(AuthorizedScope scope, UUID partyId, Instant now, UUID actorId) {
        jdbc.update(
                """
                update actionfinance.counterparty_supply
                set active = false, version = version + 1, updated_at = ?, updated_by = ?
                where tenant_id = ? and company_id = ? and counterparty_id = ? and active = true
                """,
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                partyId);
    }

    public void insertExternal(AuthorizedScope scope, UUID partyId, ExternalRow row, Instant now, UUID actorId) {
        jdbc.update(
                """
                insert into actionfinance.counterparty_external_identity (
                    id, tenant_id, company_id, counterparty_id, origin_system, connection_key,
                    external_id, observed_at, created_at, created_by)
                values (?,?,?,?,?,?,?,?,?,?)
                """,
                row.id(),
                scope.tenantId(),
                scope.companyId(),
                partyId,
                row.originSystem(),
                row.connectionKey() == null ? "" : row.connectionKey(),
                row.externalId(),
                row.observedAt() == null ? null : Timestamp.from(row.observedAt()),
                Timestamp.from(now),
                actorId);
    }

    public Optional<ImportBatchRow> findPreviewByHash(AuthorizedScope scope, String sha) {
        return jdbc
                .query(
                        """
                        select * from actionfinance.counterparty_import_batch
                        where tenant_id = ? and company_id = ? and content_sha256 = ? and status = 'PREVIEW'
                        """,
                        this::mapBatch,
                        scope.tenantId(),
                        scope.companyId(),
                        sha)
                .stream()
                .findFirst();
    }

    public Optional<ImportBatchRow> findBatch(AuthorizedScope scope, UUID id) {
        return jdbc
                .query(
                        """
                        select * from actionfinance.counterparty_import_batch
                        where tenant_id = ? and company_id = ? and id = ?
                        """,
                        this::mapBatch,
                        scope.tenantId(),
                        scope.companyId(),
                        id)
                .stream()
                .findFirst();
    }

    public Optional<ImportBatchRow> lockBatch(AuthorizedScope scope, UUID id) {
        return jdbc
                .query(
                        """
                        select * from actionfinance.counterparty_import_batch
                        where tenant_id = ? and company_id = ? and id = ?
                        for update
                        """,
                        this::mapBatch,
                        scope.tenantId(),
                        scope.companyId(),
                        id)
                .stream()
                .findFirst();
    }

    public void insertBatch(AuthorizedScope scope, ImportBatchRow row, UUID actorId, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.counterparty_import_batch (
                    id, tenant_id, company_id, filename, content_sha256, status, total_lines,
                    column_map, created_at, created_by)
                values (?,?,?,?,?,?,?,cast(? as jsonb),?,?)
                """,
                row.id(),
                scope.tenantId(),
                scope.companyId(),
                row.filename(),
                row.contentSha(),
                row.status(),
                row.totalLines(),
                json(row.columnMap()),
                Timestamp.from(now),
                actorId);
    }

    public void insertLine(AuthorizedScope scope, ImportLineRow row) {
        jdbc.update(
                """
                insert into actionfinance.counterparty_import_line (
                    id, tenant_id, company_id, batch_id, line_no, raw, classification, selected,
                    match_counterparty_id, preview_version, result, error_message, idempotency_key)
                values (?,?,?,?,?,cast(? as jsonb),?,?,?,?,?,?,?)
                """,
                row.id(),
                scope.tenantId(),
                scope.companyId(),
                row.batchId(),
                row.lineNo(),
                json(row.raw()),
                row.classification(),
                row.selected(),
                row.matchId(),
                row.previewVersion(),
                row.result(),
                row.errorMessage(),
                row.idempotencyKey());
    }

    public List<ImportLineRow> listLines(AuthorizedScope scope, UUID batchId) {
        return jdbc.query(
                """
                select * from actionfinance.counterparty_import_line
                where tenant_id = ? and company_id = ? and batch_id = ?
                order by line_no
                """,
                this::mapLine,
                scope.tenantId(),
                scope.companyId(),
                batchId);
    }

    public Optional<ImportLineRow> lockLine(AuthorizedScope scope, UUID lineId) {
        return jdbc
                .query(
                        """
                        select * from actionfinance.counterparty_import_line
                        where tenant_id = ? and company_id = ? and id = ?
                        for update
                        """,
                        this::mapLine,
                        scope.tenantId(),
                        scope.companyId(),
                        lineId)
                .stream()
                .findFirst();
    }

    public void updateLineResult(AuthorizedScope scope, UUID lineId, boolean selected, String result, String error) {
        jdbc.update(
                """
                update actionfinance.counterparty_import_line
                set selected = ?, result = ?, error_message = ?
                where tenant_id = ? and company_id = ? and id = ?
                """,
                selected,
                result,
                error,
                scope.tenantId(),
                scope.companyId(),
                lineId);
    }

    public void markBatchConfirmed(AuthorizedScope scope, UUID id, Instant now, UUID actorId) {
        jdbc.update(
                """
                update actionfinance.counterparty_import_batch
                set status = 'CONFIRMED', confirmed_at = ?, confirmed_by = ?
                where tenant_id = ? and company_id = ? and id = ?
                """,
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                id);
    }

    public ImportBatchView toView(ImportBatchRow batch, List<ImportLineRow> lines, ImportReport report) {
        List<ImportLineView> views = lines.stream()
                .map(line -> new ImportLineView(
                        line.id(),
                        line.lineNo(),
                        line.classification(),
                        line.selected(),
                        line.matchId(),
                        line.raw().getOrDefault("name", ""),
                        line.raw().getOrDefault("role", ""),
                        DocumentNumbers.mask(DocumentNumbers.normalizeToken(line.raw().get("documentNumber")), false),
                        line.errorMessage(),
                        line.result()))
                .toList();
        int news = (int) lines.stream().filter(l -> "NEW".equals(l.classification())).count();
        int dups = (int) lines.stream().filter(l -> "DUPLICATE".equals(l.classification())).count();
        int conflicts = (int) lines.stream().filter(l -> "CONFLICT".equals(l.classification())).count();
        int invalids = (int) lines.stream().filter(l -> "INVALID".equals(l.classification())).count();
        return new ImportBatchView(
                batch.id(),
                batch.filename(),
                batch.status(),
                batch.totalLines(),
                news,
                dups,
                conflicts,
                invalids,
                "PER_LINE",
                views,
                report);
    }

    public PartyDetail toDetail(
            PartyRow row,
            boolean reveal,
            boolean referenced,
            br.com.actionfinance.application.finance.PartyRecords.PartyCompleteness completeness,
            List<PartyUnitView> units,
            List<PartyAddressView> addresses,
            List<PartyContactView> contacts,
            List<PartySupplyView> supplies,
            List<PartyExternalView> externals,
            List<PartyHistoryView> history) {
        return new PartyDetail(
                row.id(),
                row.code(),
                row.name(),
                row.tradeName(),
                row.personKind(),
                row.role(),
                row.active(),
                row.documentPending(),
                row.documentCountry(),
                row.documentType(),
                reveal ? row.documentNumber() : null,
                DocumentNumbers.mask(row.documentNormalized(), reveal),
                row.originKind(),
                row.notes(),
                row.version(),
                row.createdAt(),
                row.updatedAt(),
                row.createdBy(),
                row.updatedBy(),
                referenced,
                completeness,
                units,
                addresses,
                contacts,
                supplies,
                externals,
                history);
    }

    private ImportBatchRow mapBatch(java.sql.ResultSet rs, int rowNum) throws java.sql.SQLException {
        return new ImportBatchRow(
                rs.getObject("id", UUID.class),
                rs.getString("filename"),
                rs.getString("content_sha256"),
                rs.getString("status"),
                rs.getInt("total_lines"),
                readMap(rs.getString("column_map")),
                rs.getTimestamp("created_at").toInstant());
    }

    private ImportLineRow mapLine(java.sql.ResultSet rs, int rowNum) throws java.sql.SQLException {
        return new ImportLineRow(
                rs.getObject("id", UUID.class),
                rs.getObject("batch_id", UUID.class),
                rs.getInt("line_no"),
                readMap(rs.getString("raw")),
                rs.getString("classification"),
                rs.getBoolean("selected"),
                rs.getObject("match_counterparty_id", UUID.class),
                (Long) rs.getObject("preview_version"),
                rs.getString("result"),
                rs.getString("error_message"),
                rs.getString("idempotency_key"));
    }

    private static DocumentType optionalType(String raw) {
        return raw == null || raw.isBlank() ? null : DocumentType.valueOf(raw);
    }

    private String json(Object value) {
        try {
            return mapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException(ex);
        }
    }

    private Map<String, String> readMap(String raw) {
        if (raw == null || raw.isBlank()) {
            return Map.of();
        }
        try {
            return mapper.readValue(raw, new TypeReference<LinkedHashMap<String, String>>() {});
        } catch (JsonProcessingException ex) {
            return Map.of();
        }
    }
}
