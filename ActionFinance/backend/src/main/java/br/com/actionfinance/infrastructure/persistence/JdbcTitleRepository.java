package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.FinancialFilter;
import br.com.actionfinance.application.finance.TitleListQuery;
import br.com.actionfinance.application.finance.TitleSummary;
import br.com.actionfinance.application.finance.TitleView;
import br.com.actionfinance.domain.HistoryAction;
import br.com.actionfinance.domain.OriginKind;
import br.com.actionfinance.domain.SettlementStatus;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.domain.TitleStatus;
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
public class JdbcTitleRepository {

    private final JdbcTemplate jdbc;

    public JdbcTitleRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final String SETTLED_SQL =
            """
            coalesce((
              select sum(a.amount_minor)
              from actionfinance.settlement_allocation a
              where a.tenant_id = t.tenant_id
                and a.company_id = t.company_id
                and a.title_id = t.id
                and not exists (
                  select 1 from actionfinance.settlement_reversal r
                  where r.tenant_id = a.tenant_id
                    and r.company_id = a.company_id
                    and r.settlement_id = a.settlement_id
                )
            ), 0)
            """;

    private static final String TITLE_SELECT =
            """
            select t.*,
                   cp.code as counterparty_code, cp.name as counterparty_name, cp.active as counterparty_active,
                   cat.code as category_code, cat.name as category_name, cat.active as category_active,
                   c.is_demo as company_demo,
            """
                    + SETTLED_SQL
                    + " as settled_amount_minor\n"
                    + """
            from actionfinance.financial_title t
            left join actionfinance.counterparty cp
              on cp.tenant_id = t.tenant_id and cp.company_id = t.company_id and cp.id = t.counterparty_id
            left join actionfinance.financial_category cat
              on cat.tenant_id = t.tenant_id and cat.company_id = t.company_id and cat.id = t.category_id
            join actionfinance.company c
              on c.tenant_id = t.tenant_id and c.id = t.company_id
            """;

    private TitleView mapTitle(java.sql.ResultSet rs, LocalDate businessDate) throws java.sql.SQLException {
        LocalDate due = rs.getDate("due_date") == null ? null : rs.getDate("due_date").toLocalDate();
        TitleStatus status = TitleStatus.valueOf(rs.getString("status"));
        BigDecimal amount = rs.getBigDecimal("amount_minor");
        BigDecimal settled = rs.getBigDecimal("settled_amount_minor");
        if (settled == null) {
            settled = BigDecimal.ZERO;
        }
        BigDecimal outstanding = amount == null ? BigDecimal.ZERO : amount.subtract(settled);
        SettlementStatus settlementStatus = SettlementStatus.derive(status, amount, settled);
        boolean overdue = status == TitleStatus.OPEN
                && outstanding.signum() > 0
                && due != null
                && due.isBefore(businessDate);
        return new TitleView(
                rs.getObject("id", UUID.class),
                rs.getObject("tenant_id", UUID.class),
                rs.getObject("company_id", UUID.class),
                rs.getString("reference"),
                TitleDirection.valueOf(rs.getString("direction")),
                status,
                rs.getString("description"),
                rs.getObject("counterparty_id", UUID.class),
                rs.getString("counterparty_code"),
                rs.getString("counterparty_name"),
                rs.getObject("counterparty_active") != null && rs.getBoolean("counterparty_active"),
                rs.getObject("category_id", UUID.class),
                rs.getString("category_code"),
                rs.getString("category_name"),
                rs.getObject("category_active") != null && rs.getBoolean("category_active"),
                amount,
                rs.getString("currency"),
                rs.getDate("competence_date") == null ? null : rs.getDate("competence_date").toLocalDate(),
                due,
                overdue,
                OriginKind.valueOf(rs.getString("origin_kind")),
                rs.getString("source_reference"),
                rs.getLong("version"),
                rs.getTimestamp("created_at").toInstant(),
                rs.getTimestamp("updated_at").toInstant(),
                rs.getObject("created_by", UUID.class),
                rs.getObject("updated_by", UUID.class),
                rs.getTimestamp("confirmed_at") == null ? null : rs.getTimestamp("confirmed_at").toInstant(),
                rs.getTimestamp("cancelled_at") == null ? null : rs.getTimestamp("cancelled_at").toInstant(),
                rs.getString("cancellation_reason"),
                rs.getBoolean("company_demo"),
                settled,
                outstanding,
                settlementStatus);
    }

    public boolean hasSettlementHistory(AuthorizedScope scope, UUID titleId) {
        Boolean found = jdbc.queryForObject(
                """
                select exists (
                  select 1 from actionfinance.settlement_allocation a
                  where a.tenant_id = ? and a.company_id = ? and a.title_id = ?
                )
                """,
                Boolean.class,
                scope.tenantId(),
                scope.companyId(),
                titleId);
        return Boolean.TRUE.equals(found);
    }

    public Optional<TitleView> find(AuthorizedScope scope, TitleDirection direction, UUID id, LocalDate businessDate) {
        List<TitleView> rows = jdbc.query(
                TITLE_SELECT
                        + " where t.tenant_id = ? and t.company_id = ? and t.direction = ? and t.id = ?",
                (rs, rowNum) -> mapTitle(rs, businessDate),
                scope.tenantId(),
                scope.companyId(),
                direction.name(),
                id);
        return rows.stream().findFirst();
    }

    public Optional<TitleView> lock(AuthorizedScope scope, TitleDirection direction, UUID id, LocalDate businessDate) {
        List<TitleView> rows = jdbc.query(
                TITLE_SELECT
                        + " where t.tenant_id = ? and t.company_id = ? and t.direction = ? and t.id = ? for update of t",
                (rs, rowNum) -> mapTitle(rs, businessDate),
                scope.tenantId(),
                scope.companyId(),
                direction.name(),
                id);
        return rows.stream().findFirst();
    }

    public void insert(TitleView title) {
        jdbc.update(
                """
                insert into actionfinance.financial_title (
                    id, tenant_id, company_id, reference, direction, status, description,
                    counterparty_id, category_id, amount_minor, currency, competence_date, due_date,
                    origin_kind, source_reference, version, created_at, updated_at, created_by, updated_by,
                    confirmed_at, cancelled_at, cancellation_reason)
                values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                title.id(),
                title.tenantId(),
                title.companyId(),
                title.reference(),
                title.direction().name(),
                title.status().name(),
                title.description(),
                title.counterpartyId(),
                title.categoryId(),
                title.amountMinor(),
                title.currency(),
                title.competenceDate() == null ? null : Date.valueOf(title.competenceDate()),
                title.dueDate() == null ? null : Date.valueOf(title.dueDate()),
                title.originKind().name(),
                title.sourceReference(),
                title.version(),
                Timestamp.from(title.createdAt()),
                Timestamp.from(title.updatedAt()),
                title.createdBy(),
                title.updatedBy(),
                title.confirmedAt() == null ? null : Timestamp.from(title.confirmedAt()),
                title.cancelledAt() == null ? null : Timestamp.from(title.cancelledAt()),
                title.cancellationReason());
    }

    public int update(TitleView title, long expectedVersion) {
        return jdbc.update(
                """
                update actionfinance.financial_title
                set status = ?, description = ?, counterparty_id = ?, category_id = ?,
                    amount_minor = ?, competence_date = ?, due_date = ?, source_reference = ?,
                    version = ?, updated_at = ?, updated_by = ?, confirmed_at = ?,
                    cancelled_at = ?, cancellation_reason = ?
                where tenant_id = ? and company_id = ? and id = ? and version = ?
                """,
                title.status().name(),
                title.description(),
                title.counterpartyId(),
                title.categoryId(),
                title.amountMinor(),
                title.competenceDate() == null ? null : Date.valueOf(title.competenceDate()),
                title.dueDate() == null ? null : Date.valueOf(title.dueDate()),
                title.sourceReference(),
                title.version(),
                Timestamp.from(title.updatedAt()),
                title.updatedBy(),
                title.confirmedAt() == null ? null : Timestamp.from(title.confirmedAt()),
                title.cancelledAt() == null ? null : Timestamp.from(title.cancelledAt()),
                title.cancellationReason(),
                title.tenantId(),
                title.companyId(),
                title.id(),
                expectedVersion);
    }

    public void insertHistory(UUID id, TitleView title, HistoryAction action, UUID actorId, String actorName, Instant at, String reason, String changesJson) {
        jdbc.update(
                """
                insert into actionfinance.financial_title_history (
                    id, tenant_id, company_id, title_id, title_version, action,
                    actor_id, actor_display_name, occurred_at, reason, changes)
                values (?,?,?,?,?,?,?,?,?,?,?::jsonb)
                """,
                id,
                title.tenantId(),
                title.companyId(),
                title.id(),
                title.version(),
                action.name(),
                actorId,
                actorName,
                Timestamp.from(at),
                reason,
                changesJson);
    }

    public List<TitleView.HistoryEntry> history(AuthorizedScope scope, UUID titleId) {
        return jdbc.query(
                """
                select id, title_version, action, actor_id, actor_display_name, occurred_at, reason, changes::text as changes
                from actionfinance.financial_title_history
                where tenant_id = ? and company_id = ? and title_id = ?
                order by occurred_at desc, title_version desc, id desc
                """,
                (rs, rowNum) -> new TitleView.HistoryEntry(
                        rs.getObject("id", UUID.class),
                        rs.getLong("title_version"),
                        HistoryAction.valueOf(rs.getString("action")),
                        rs.getObject("actor_id", UUID.class),
                        rs.getString("actor_display_name"),
                        rs.getTimestamp("occurred_at").toInstant(),
                        rs.getString("reason"),
                        rs.getString("changes")),
                scope.tenantId(),
                scope.companyId(),
                titleId);
    }

    public TitleView.Page list(
            AuthorizedScope scope,
            TitleDirection direction,
            TitleListQuery query,
            LocalDate businessDate) {
        FilterSql filter = buildFilter(scope, direction, query, businessDate);
        Long total = jdbc.queryForObject(
                "select count(*) from actionfinance.financial_title t " + filter.join + " where " + filter.where,
                Long.class,
                filter.args.toArray());
        List<TitleView> items = jdbc.query(
                TITLE_SELECT
                        + " where "
                        + filter.where
                        + " order by t.due_date asc nulls last, t.id asc limit ? offset ?",
                (rs, rowNum) -> mapTitle(rs, businessDate),
                append(filter.args, query.size(), query.page() * query.size()).toArray());
        TitleSummary summary = summary(scope, direction, query, businessDate);
        return new TitleView.Page(items, total == null ? 0 : total, query.page(), query.size(), summary, businessDate);
    }

    public TitleSummary summary(
            AuthorizedScope scope, TitleDirection direction, TitleListQuery query, LocalDate businessDate) {
        FilterSql filter = buildFilter(scope, direction, query, businessDate);
        return jdbc.queryForObject(
                """
                select
                  count(*) filter (where t.status = 'OPEN' and t.amount_minor is not null and (t.amount_minor - (
            """
                        + SETTLED_SQL
                        + """
                  )) > 0) as open_count,
                  coalesce(sum((t.amount_minor - (
            """
                        + SETTLED_SQL
                        + """
                  ))) filter (where t.status = 'OPEN' and t.amount_minor is not null and (t.amount_minor - (
            """
                        + SETTLED_SQL
                        + """
                  )) > 0), 0) as open_amount,
                  count(*) filter (where t.status = 'OPEN' and t.due_date is not null and t.due_date < ? and t.amount_minor is not null and (t.amount_minor - (
            """
                        + SETTLED_SQL
                        + """
                  )) > 0) as overdue_count,
                  coalesce(sum((t.amount_minor - (
            """
                        + SETTLED_SQL
                        + """
                  ))) filter (where t.status = 'OPEN' and t.due_date is not null and t.due_date < ? and t.amount_minor is not null and (t.amount_minor - (
            """
                        + SETTLED_SQL
                        + """
                  )) > 0), 0) as overdue_amount,
                  count(*) filter (where t.status = 'DRAFT') as draft_count
                from actionfinance.financial_title t
                """
                        + filter.join
                        + " where "
                        + filter.where,
                (rs, rowNum) -> new TitleSummary(
                        rs.getLong("open_count"),
                        rs.getBigDecimal("open_amount"),
                        rs.getLong("overdue_count"),
                        rs.getBigDecimal("overdue_amount"),
                        rs.getLong("draft_count")),
                prepend(filter.args, businessDate, businessDate).toArray());
    }

    public void insertIdempotency(
            UUID id,
            AuthorizedScope scope,
            UUID actorId,
            String operation,
            String key,
            String hash,
            UUID resourceId,
            int status,
            String bodyJson,
            Instant at) {
        jdbc.update(
                """
                insert into actionfinance.request_idempotency (
                    id, tenant_id, company_id, actor_id, operation, idempotency_key,
                    request_hash, resource_id, response_status, response_body, created_at)
                values (?,?,?,?,?,?,?,?,?,?::jsonb,?)
                """,
                id,
                scope.tenantId(),
                scope.companyId(),
                actorId,
                operation,
                key,
                hash,
                resourceId,
                status,
                bodyJson,
                Timestamp.from(at));
    }

    public Optional<IdempotencyRow> findIdempotency(AuthorizedScope scope, UUID actorId, String operation, String key) {
        List<IdempotencyRow> rows = jdbc.query(
                """
                select request_hash, resource_id, response_status, response_body::text as body
                from actionfinance.request_idempotency
                where tenant_id = ? and company_id = ? and actor_id = ? and operation = ? and idempotency_key = ?
                """,
                (rs, rowNum) -> new IdempotencyRow(
                        rs.getString("request_hash"),
                        rs.getObject("resource_id", UUID.class),
                        rs.getInt("response_status"),
                        rs.getString("body")),
                scope.tenantId(),
                scope.companyId(),
                actorId,
                operation,
                key);
        return rows.stream().findFirst();
    }

    public void advisoryLock(AuthorizedScope scope, UUID actorId, String operation, String key) {
        String token = scope.tenantId() + "|" + scope.companyId() + "|" + actorId + "|" + operation + "|" + key;
        jdbc.execute(
                (java.sql.Connection connection) -> {
                    try (var statement = connection.prepareStatement("select pg_advisory_xact_lock(hashtext(?))")) {
                        statement.setString(1, token);
                        statement.execute();
                    }
                    return null;
                });
    }

    public record IdempotencyRow(String requestHash, UUID resourceId, int status, String bodyJson) {}

    private record FilterSql(String join, String where, List<Object> args) {}

    private static FilterSql buildFilter(
            AuthorizedScope scope, TitleDirection direction, TitleListQuery query, LocalDate businessDate) {
        List<Object> args = new ArrayList<>();
        StringBuilder where = new StringBuilder("t.tenant_id = ? and t.company_id = ? and t.direction = ?");
        args.add(scope.tenantId());
        args.add(scope.companyId());
        args.add(direction.name());
        String join = "";
        if (query.search() != null && !query.search().isBlank()) {
            join = " left join actionfinance.counterparty cp on cp.tenant_id = t.tenant_id and cp.company_id = t.company_id and cp.id = t.counterparty_id ";
            where.append(
                    " and (t.reference ilike ? escape '\\' or t.description ilike ? escape '\\' or coalesce(cp.name,'') ilike ? escape '\\')");
            String like = "%" + escapeLike(query.search().trim()) + "%";
            args.add(like);
            args.add(like);
            args.add(like);
        }
        if (!query.allStatuses() && query.status() != null) {
            where.append(" and t.status = ?");
            args.add(query.status().name());
        }
        if (query.dueFrom() != null) {
            where.append(" and t.due_date >= ?");
            args.add(Date.valueOf(query.dueFrom()));
        }
        if (query.dueTo() != null) {
            where.append(" and t.due_date <= ?");
            args.add(Date.valueOf(query.dueTo()));
        }
        if (query.categoryId() != null) {
            where.append(" and t.category_id = ?");
            args.add(query.categoryId());
        }
        if (query.overdueOnly()) {
            where.append(" and t.status = 'OPEN' and t.due_date is not null and t.due_date < ?");
            where.append(" and t.amount_minor is not null and (t.amount_minor - (").append(SETTLED_SQL).append(")) > 0");
            args.add(Date.valueOf(businessDate));
        }
        boolean ignoreFinancial = query.status() == TitleStatus.DRAFT || query.status() == TitleStatus.CANCELLED;
        FinancialFilter financial = query.financial() == null ? FinancialFilter.PENDING : query.financial();
        if (!ignoreFinancial && financial != FinancialFilter.ALL) {
            String outstanding = "(t.amount_minor - (" + SETTLED_SQL + "))";
            if (financial == FinancialFilter.PENDING) {
                where.append(" and (t.status <> 'OPEN' or (t.amount_minor is not null and ")
                        .append(outstanding)
                        .append(" > 0))");
            } else if (financial == FinancialFilter.PARTIAL) {
                where.append(" and t.status = 'OPEN' and (").append(SETTLED_SQL).append(") > 0 and ")
                        .append(outstanding)
                        .append(" > 0");
            } else if (financial == FinancialFilter.SETTLED) {
                where.append(" and t.status = 'OPEN' and t.amount_minor is not null and ")
                        .append(outstanding)
                        .append(" = 0");
            }
        }
        return new FilterSql(join, where.toString(), args);
    }

    private static String escapeLike(String raw) {
        return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }

    private static List<Object> append(List<Object> base, Object... extra) {
        List<Object> copy = new ArrayList<>(base);
        copy.addAll(List.of(extra));
        return copy;
    }

    private static List<Object> prepend(List<Object> base, Object... extra) {
        List<Object> copy = new ArrayList<>(List.of(extra));
        copy.addAll(base);
        return copy;
    }
}
