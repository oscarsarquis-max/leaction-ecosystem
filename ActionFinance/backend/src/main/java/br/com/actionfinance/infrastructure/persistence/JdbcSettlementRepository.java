package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.SettlementView;
import br.com.actionfinance.domain.OriginKind;
import br.com.actionfinance.domain.SettlementMethod;
import br.com.actionfinance.domain.TitleDirection;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcSettlementRepository {

    private final JdbcTemplate jdbc;

    public JdbcSettlementRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final String SELECT =
            """
            select s.*,
                   a.title_id,
                   t.reference as title_reference,
                   t.description as title_description,
                   t.direction as title_direction,
                   t.version as title_version,
                   cp.name as counterparty_name,
                   acc.name as account_name,
                   acc.active as account_active,
                   r.id as reversal_id,
                   r.effective_date as reversal_effective_date,
                   r.reason as reversal_reason,
                   r.recorded_at as reversal_recorded_at,
                   r.actor_display_name as reversal_actor_display_name,
                   ms.id as movement_id,
                   mr.id as reversal_movement_id
            from actionfinance.settlement s
            join actionfinance.settlement_allocation a
              on a.tenant_id = s.tenant_id and a.company_id = s.company_id and a.settlement_id = s.id
            join actionfinance.financial_title t
              on t.tenant_id = a.tenant_id and t.company_id = a.company_id and t.id = a.title_id
            left join actionfinance.counterparty cp
              on cp.tenant_id = t.tenant_id and cp.company_id = t.company_id and cp.id = t.counterparty_id
            join actionfinance.financial_account acc
              on acc.tenant_id = s.tenant_id and acc.company_id = s.company_id and acc.id = s.account_id
            left join actionfinance.settlement_reversal r
              on r.tenant_id = s.tenant_id and r.company_id = s.company_id and r.settlement_id = s.id
            left join actionfinance.cash_movement ms
              on ms.tenant_id = s.tenant_id and ms.company_id = s.company_id
             and ms.settlement_id = s.id and ms.kind = 'SETTLEMENT'
            left join actionfinance.cash_movement mr
              on mr.tenant_id = s.tenant_id and mr.company_id = s.company_id
             and mr.reversal_id = r.id and mr.kind = 'REVERSAL'
            """;

    public Optional<SettlementView> find(AuthorizedScope scope, UUID id) {
        List<SettlementView> rows = jdbc.query(
                SELECT + " where s.tenant_id = ? and s.company_id = ? and s.id = ?",
                (rs, rowNum) -> map(rs),
                scope.tenantId(),
                scope.companyId(),
                id);
        return rows.stream().findFirst();
    }

    public List<SettlementView> listForTitle(AuthorizedScope scope, UUID titleId) {
        return jdbc.query(
                SELECT
                        + " where s.tenant_id = ? and s.company_id = ? and a.title_id = ? order by s.effective_date desc, s.recorded_at desc, s.id desc",
                (rs, rowNum) -> map(rs),
                scope.tenantId(),
                scope.companyId(),
                titleId);
    }

    public boolean hasReversal(AuthorizedScope scope, UUID settlementId) {
        Boolean found = jdbc.queryForObject(
                """
                select exists (
                  select 1 from actionfinance.settlement_reversal
                  where tenant_id = ? and company_id = ? and settlement_id = ?
                )
                """,
                Boolean.class,
                scope.tenantId(),
                scope.companyId(),
                settlementId);
        return Boolean.TRUE.equals(found);
    }

    public void insertSettlement(
            UUID id,
            AuthorizedScope scope,
            UUID accountId,
            TitleDirection direction,
            BigDecimal amount,
            LocalDate effectiveDate,
            SettlementMethod method,
            String note,
            Instant at,
            UUID actor,
            String actorName) {
        jdbc.update(
                """
                insert into actionfinance.settlement (
                    id, tenant_id, company_id, account_id, direction, amount_minor, currency,
                    effective_date, method, note, origin_kind, recorded_at, recorded_by, actor_display_name)
                values (?,?,?,?,?,?,'BRL',?,?,?,'MANUAL',?,?,?)
                """,
                id,
                scope.tenantId(),
                scope.companyId(),
                accountId,
                direction.name(),
                amount,
                Date.valueOf(effectiveDate),
                method.name(),
                note,
                Timestamp.from(at),
                actor,
                actorName);
    }

    public void insertAllocation(UUID id, AuthorizedScope scope, UUID settlementId, UUID titleId, BigDecimal amount) {
        jdbc.update(
                """
                insert into actionfinance.settlement_allocation (
                    id, tenant_id, company_id, settlement_id, title_id, amount_minor)
                values (?,?,?,?,?,?)
                """,
                id,
                scope.tenantId(),
                scope.companyId(),
                settlementId,
                titleId,
                amount);
    }

    public void insertReversal(
            UUID id,
            AuthorizedScope scope,
            UUID settlementId,
            LocalDate effectiveDate,
            String reason,
            Instant at,
            UUID actor,
            String actorName) {
        jdbc.update(
                """
                insert into actionfinance.settlement_reversal (
                    id, tenant_id, company_id, settlement_id, effective_date, reason,
                    recorded_at, recorded_by, actor_display_name)
                values (?,?,?,?,?,?,?,?,?)
                """,
                id,
                scope.tenantId(),
                scope.companyId(),
                settlementId,
                Date.valueOf(effectiveDate),
                reason,
                Timestamp.from(at),
                actor,
                actorName);
    }

    public int bumpTitleVersion(AuthorizedScope scope, UUID titleId, long expectedVersion, Instant at, UUID actor) {
        return jdbc.update(
                """
                update actionfinance.financial_title
                set version = version + 1, updated_at = ?, updated_by = ?
                where tenant_id = ? and company_id = ? and id = ? and version = ?
                """,
                Timestamp.from(at),
                actor,
                scope.tenantId(),
                scope.companyId(),
                titleId,
                expectedVersion);
    }

    private static SettlementView map(java.sql.ResultSet rs) throws java.sql.SQLException {
        UUID reversalId = rs.getObject("reversal_id", UUID.class);
        return new SettlementView(
                rs.getObject("id", UUID.class),
                rs.getObject("tenant_id", UUID.class),
                rs.getObject("company_id", UUID.class),
                rs.getObject("title_id", UUID.class),
                rs.getString("title_reference"),
                rs.getString("title_description"),
                rs.getString("counterparty_name"),
                TitleDirection.valueOf(rs.getString("title_direction")),
                rs.getObject("account_id", UUID.class),
                rs.getString("account_name"),
                rs.getBoolean("account_active"),
                rs.getBigDecimal("amount_minor"),
                rs.getString("currency"),
                rs.getDate("effective_date").toLocalDate(),
                SettlementMethod.valueOf(rs.getString("method")),
                rs.getString("note"),
                OriginKind.valueOf(rs.getString("origin_kind")),
                rs.getTimestamp("recorded_at").toInstant(),
                rs.getObject("recorded_by", UUID.class),
                rs.getString("actor_display_name"),
                reversalId != null,
                reversalId,
                rs.getDate("reversal_effective_date") == null ? null : rs.getDate("reversal_effective_date").toLocalDate(),
                rs.getString("reversal_reason"),
                rs.getTimestamp("reversal_recorded_at") == null ? null : rs.getTimestamp("reversal_recorded_at").toInstant(),
                rs.getString("reversal_actor_display_name"),
                rs.getObject("movement_id", UUID.class),
                rs.getObject("reversal_movement_id", UUID.class),
                BigDecimal.ZERO,
                BigDecimal.ZERO,
                rs.getLong("title_version"));
    }
}
