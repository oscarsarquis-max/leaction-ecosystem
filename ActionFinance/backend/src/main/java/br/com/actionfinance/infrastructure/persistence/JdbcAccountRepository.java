package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.finance.AccountView;
import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.MovementView;
import br.com.actionfinance.domain.AccountType;
import br.com.actionfinance.domain.MovementKind;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcAccountRepository {

    private final JdbcTemplate jdbc;

    public JdbcAccountRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final String ACCOUNT_SELECT =
            """
            select a.*, c.name as company_name,
                   coalesce((
                     select sum(m.signed_amount_minor)
                     from actionfinance.cash_movement m
                     where m.tenant_id = a.tenant_id and m.company_id = a.company_id and m.account_id = a.id
                   ), 0) as current_balance_minor
            from actionfinance.financial_account a
            join actionfinance.company c
              on c.tenant_id = a.tenant_id and c.id = a.company_id
            """;

    public Optional<AccountView> find(AuthorizedScope scope, UUID id) {
        List<AccountView> rows = jdbc.query(
                ACCOUNT_SELECT + " where a.tenant_id = ? and a.company_id = ? and a.id = ?",
                (rs, rowNum) -> mapAccount(rs),
                scope.tenantId(),
                scope.companyId(),
                id);
        return rows.stream().findFirst();
    }

    public Optional<AccountView> lock(AuthorizedScope scope, UUID id) {
        List<AccountView> rows = jdbc.query(
                ACCOUNT_SELECT + " where a.tenant_id = ? and a.company_id = ? and a.id = ? for update of a",
                (rs, rowNum) -> mapAccount(rs),
                scope.tenantId(),
                scope.companyId(),
                id);
        return rows.stream().findFirst();
    }

    public List<AccountView> list(AuthorizedScope scope) {
        return jdbc.query(
                ACCOUNT_SELECT
                        + " where a.tenant_id = ? and a.company_id = ? order by a.active desc, a.name asc, a.id asc",
                (rs, rowNum) -> mapAccount(rs),
                scope.tenantId(),
                scope.companyId());
    }

    public void insert(AccountView account, UUID actor, Instant at) {
        jdbc.update(
                """
                insert into actionfinance.financial_account (
                    id, tenant_id, company_id, code, name, type, currency, active, opened_on,
                    version, created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,?,'BRL',?,?,?,?,?,?,?)
                """,
                account.id(),
                account.tenantId(),
                account.companyId(),
                account.code(),
                account.name(),
                account.type().name(),
                account.active(),
                Date.valueOf(account.openedOn()),
                account.version(),
                Timestamp.from(at),
                Timestamp.from(at),
                actor,
                actor);
    }

    public int update(AuthorizedScope scope, UUID id, String name, Boolean active, long expectedVersion, Instant at, UUID actor) {
        return jdbc.update(
                """
                update actionfinance.financial_account
                set name = coalesce(?, name),
                    active = coalesce(?, active),
                    version = version + 1,
                    updated_at = ?,
                    updated_by = ?
                where tenant_id = ? and company_id = ? and id = ? and version = ?
                """,
                name,
                active,
                Timestamp.from(at),
                actor,
                scope.tenantId(),
                scope.companyId(),
                id,
                expectedVersion);
    }

    public void insertHistory(
            UUID id,
            AuthorizedScope scope,
            UUID accountId,
            long version,
            String action,
            UUID actor,
            Instant at,
            String changesJson) {
        jdbc.update(
                """
                insert into actionfinance.financial_account_history (
                    id, tenant_id, company_id, account_id, account_version, action, actor_id, occurred_at, changes)
                values (?,?,?,?,?,?,?,?,?::jsonb)
                """,
                id,
                scope.tenantId(),
                scope.companyId(),
                accountId,
                version,
                action,
                actor,
                Timestamp.from(at),
                changesJson);
    }

    public void insertOpening(AuthorizedScope scope, UUID id, UUID accountId, BigDecimal signed, LocalDate openedOn, Instant at, UUID actor, String description) {
        jdbc.update(
                """
                insert into actionfinance.cash_movement (
                    id, tenant_id, company_id, account_id, kind, signed_amount_minor, currency,
                    effective_date, recorded_at, recorded_by, settlement_id, reversal_id, description)
                values (?,?,?,?,'OPENING',?,'BRL',?,?,?,null,null,?)
                """,
                id,
                scope.tenantId(),
                scope.companyId(),
                accountId,
                signed,
                Date.valueOf(openedOn),
                Timestamp.from(at),
                actor,
                description);
    }

    public void insertMovement(
            UUID id,
            AuthorizedScope scope,
            UUID accountId,
            MovementKind kind,
            BigDecimal signed,
            LocalDate effectiveDate,
            Instant at,
            UUID actor,
            UUID settlementId,
            UUID reversalId,
            String description) {
        jdbc.update(
                """
                insert into actionfinance.cash_movement (
                    id, tenant_id, company_id, account_id, kind, signed_amount_minor, currency,
                    effective_date, recorded_at, recorded_by, settlement_id, reversal_id, description)
                values (?,?,?,?,?,?,'BRL',?,?,?,?,?,?)
                """,
                id,
                scope.tenantId(),
                scope.companyId(),
                accountId,
                kind.name(),
                signed,
                Date.valueOf(effectiveDate),
                Timestamp.from(at),
                actor,
                settlementId,
                reversalId,
                description);
    }

    public MovementView.Page listMovements(
            AuthorizedScope scope, UUID accountId, LocalDate from, LocalDate to, int page, int size) {
        List<Object> args = new ArrayList<>();
        args.add(scope.tenantId());
        args.add(scope.companyId());
        args.add(accountId);
        args.add(Date.valueOf(from));
        args.add(Date.valueOf(to));
        Long total = jdbc.queryForObject(
                """
                select count(*) from actionfinance.cash_movement
                where tenant_id = ? and company_id = ? and account_id = ?
                  and effective_date >= ? and effective_date <= ?
                """,
                Long.class,
                args.toArray());
        BigDecimal previous = jdbc.queryForObject(
                """
                select coalesce(sum(signed_amount_minor), 0) from actionfinance.cash_movement
                where tenant_id = ? and company_id = ? and account_id = ? and effective_date < ?
                """,
                BigDecimal.class,
                scope.tenantId(),
                scope.companyId(),
                accountId,
                Date.valueOf(from));
        BigDecimal periodSum = jdbc.queryForObject(
                """
                select coalesce(sum(signed_amount_minor), 0) from actionfinance.cash_movement
                where tenant_id = ? and company_id = ? and account_id = ?
                  and effective_date >= ? and effective_date <= ?
                """,
                BigDecimal.class,
                scope.tenantId(),
                scope.companyId(),
                accountId,
                Date.valueOf(from),
                Date.valueOf(to));
        BigDecimal current = jdbc.queryForObject(
                """
                select coalesce(sum(signed_amount_minor), 0) from actionfinance.cash_movement
                where tenant_id = ? and company_id = ? and account_id = ?
                """,
                BigDecimal.class,
                scope.tenantId(),
                scope.companyId(),
                accountId);
        List<MovementView> items = jdbc.query(
                """
                select * from (
                  select m.*,
                         sum(m.signed_amount_minor) over (
                           order by m.effective_date,
                                    case when m.kind = 'OPENING' then 0 else 1 end,
                                    m.recorded_at, m.id
                         ) as balance_after
                  from actionfinance.cash_movement m
                  where m.tenant_id = ? and m.company_id = ? and m.account_id = ?
                ) x
                where x.effective_date >= ? and x.effective_date <= ?
                order by x.effective_date,
                         case when x.kind = 'OPENING' then 0 else 1 end,
                         x.recorded_at, x.id
                limit ? offset ?
                """,
                (rs, rowNum) -> mapMovement(rs),
                scope.tenantId(),
                scope.companyId(),
                accountId,
                Date.valueOf(from),
                Date.valueOf(to),
                size,
                page * size);
        return new MovementView.Page(
                items,
                total == null ? 0 : total,
                page,
                size,
                previous == null ? BigDecimal.ZERO : previous,
                (previous == null ? BigDecimal.ZERO : previous).add(periodSum == null ? BigDecimal.ZERO : periodSum),
                current == null ? BigDecimal.ZERO : current,
                from,
                to);
    }

    private static AccountView mapAccount(java.sql.ResultSet rs) throws java.sql.SQLException {
        return new AccountView(
                rs.getObject("id", UUID.class),
                rs.getObject("tenant_id", UUID.class),
                rs.getObject("company_id", UUID.class),
                rs.getString("company_name"),
                rs.getString("code"),
                rs.getString("name"),
                AccountType.valueOf(rs.getString("type")),
                rs.getString("currency"),
                rs.getBoolean("active"),
                rs.getDate("opened_on").toLocalDate(),
                rs.getBigDecimal("current_balance_minor"),
                rs.getLong("version"),
                rs.getTimestamp("created_at").toInstant(),
                rs.getTimestamp("updated_at").toInstant());
    }

    private static MovementView mapMovement(java.sql.ResultSet rs) throws java.sql.SQLException {
        BigDecimal signed = rs.getBigDecimal("signed_amount_minor");
        BigDecimal inflow = signed.signum() > 0 ? signed : BigDecimal.ZERO;
        BigDecimal outflow = signed.signum() < 0 ? signed.abs() : BigDecimal.ZERO;
        return new MovementView(
                rs.getObject("id", UUID.class),
                MovementKind.valueOf(rs.getString("kind")),
                rs.getDate("effective_date").toLocalDate(),
                rs.getTimestamp("recorded_at").toInstant(),
                rs.getObject("recorded_by", UUID.class),
                rs.getString("description"),
                inflow,
                outflow,
                rs.getBigDecimal("balance_after"),
                rs.getObject("settlement_id", UUID.class),
                rs.getObject("reversal_id", UUID.class));
    }
}
