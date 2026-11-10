package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.overview.OverviewFacts;
import br.com.actionfinance.application.overview.OverviewFacts.CashReading;
import br.com.actionfinance.application.overview.OverviewFacts.CategoryAmount;
import br.com.actionfinance.application.overview.OverviewFacts.FeeReading;
import br.com.actionfinance.application.overview.OverviewFacts.MethodAmount;
import br.com.actionfinance.application.overview.OverviewFacts.OpenTitle;
import br.com.actionfinance.application.overview.OverviewStore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Date;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

@Repository
public class JdbcOverviewStore implements OverviewStore {

    private final JdbcTemplate jdbc;

    public JdbcOverviewStore(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public OverviewFacts load(
            AuthorizedScope scope,
            Instant from,
            Instant toExclusive,
            LocalDate fromDay,
            LocalDate toDay,
            LocalDate today) {
        boolean pay = Boolean.TRUE.equals(jdbc.queryForObject(
                """
                select exists(
                  select 1 from actionfinance.pay_company_mapping
                   where tenant_id = ? and company_id = ? and authorized = true)
                """,
                Boolean.class,
                scope.tenantId(),
                scope.companyId()));
        List<MethodAmount> sales = jdbc.query(
                """
                select coalesce(payment_method, ''), sum(paid_amount_minor)
                  from actionfinance.pay_receipt_transaction
                 where tenant_id = ? and company_id = ?
                   and classification = 'REAL'
                   and normalized_status = 'CONFIRMED'
                   and paid_amount_absent = false
                   and paid_amount_minor is not null
                   and origin_updated_at >= ? and origin_updated_at < ?
                 group by 1
                """,
                (rs, n) -> new MethodAmount(rs.getString(1), rs.getLong(2)),
                scope.tenantId(),
                scope.companyId(),
                Timestamp.from(from),
                Timestamp.from(toExclusive));
        FeeReading fees = jdbc.queryForObject(
                """
                select count(*) filter (where import_status = 'ACTIVE'),
                       count(*) filter (where import_status = 'ACTIVE' and fee_absent = false and fee_minor is not null),
                       coalesce(sum(fee_minor) filter (where import_status = 'ACTIVE' and fee_absent = false), 0)
                  from actionfinance.statement_line
                 where tenant_id = ? and company_id = ?
                   and effective_on >= ? and effective_on <= ?
                """,
                (rs, n) -> new FeeReading(rs.getInt(1), rs.getInt(2), rs.getLong(3)),
                scope.tenantId(),
                scope.companyId(),
                Date.valueOf(fromDay),
                Date.valueOf(toDay));
        List<CategoryAmount> expenses = jdbc.query(
                """
                select coalesce(c.name, 'Sem categoria'), sum(a.amount_minor)
                  from actionfinance.settlement s
                  join actionfinance.settlement_allocation a
                    on a.tenant_id = s.tenant_id and a.company_id = s.company_id and a.settlement_id = s.id
                  join actionfinance.financial_title t
                    on t.tenant_id = a.tenant_id and t.company_id = a.company_id and t.id = a.title_id
                  left join actionfinance.financial_category c
                    on c.tenant_id = t.tenant_id and c.company_id = t.company_id and c.id = t.category_id
                 where s.tenant_id = ? and s.company_id = ?
                   and s.direction = 'PAYABLE'
                   and s.effective_date >= ? and s.effective_date <= ?
                   and not exists (
                     select 1 from actionfinance.settlement_reversal r
                      where r.tenant_id = s.tenant_id and r.company_id = s.company_id and r.settlement_id = s.id)
                 group by 1
                 order by 2 desc
                """,
                (rs, n) -> new CategoryAmount(rs.getString(1), rs.getLong(2)),
                scope.tenantId(),
                scope.companyId(),
                Date.valueOf(fromDay),
                Date.valueOf(toDay));
        Integer accounts = jdbc.queryForObject(
                "select count(*) from actionfinance.financial_account where tenant_id = ? and company_id = ?",
                Integer.class,
                scope.tenantId(),
                scope.companyId());
        CoveredPosition covered = jdbc.queryForObject(
                """
                select count(*)::int, coalesce(sum(balance_minor), 0)
                  from (
                    select (select sum(m.signed_amount_minor) from actionfinance.cash_movement m
                             where m.tenant_id = a.tenant_id and m.company_id = a.company_id
                               and m.account_id = a.id and m.effective_date <= ?) as balance_minor
                      from actionfinance.financial_account a
                     where a.tenant_id = ? and a.company_id = ? and a.active = true and a.currency = 'BRL'
                       and exists (
                         select 1 from actionfinance.cash_movement o
                          where o.tenant_id = a.tenant_id and o.company_id = a.company_id
                            and o.account_id = a.id and o.kind = 'OPENING' and o.effective_date <= ?)
                  ) known
                """,
                (rs, n) -> new CoveredPosition(rs.getInt(1), rs.getLong(2)),
                Date.valueOf(today),
                scope.tenantId(),
                scope.companyId(),
                Date.valueOf(today));
        CashReading cash;
        if (accounts == null || accounts == 0) {
            cash = new CashReading("NAO_CONECTADO", null);
        } else if (covered == null || covered.count() == 0) {
            cash = new CashReading("NAO_APURADO", null);
        } else {
            cash = new CashReading("APURADO", covered.minor());
        }
        String accountName = jdbc.query(
                """
                select a.name from actionfinance.financial_account a
                 where a.tenant_id = ? and a.company_id = ? and a.active = true
                 order by a.name
                 limit 1
                """,
                (rs, n) -> rs.getString(1),
                scope.tenantId(),
                scope.companyId()).stream().findFirst().orElse(null);
        List<OpenTitle> titles = jdbc.query(
                """
                select t.direction, t.description, t.due_date,
                       t.amount_minor - coalesce((
                         select sum(a.amount_minor)
                           from actionfinance.settlement_allocation a
                           join actionfinance.settlement s
                             on s.tenant_id = a.tenant_id and s.company_id = a.company_id and s.id = a.settlement_id
                          where a.tenant_id = t.tenant_id and a.company_id = t.company_id and a.title_id = t.id
                            and not exists (
                              select 1 from actionfinance.settlement_reversal r
                               where r.tenant_id = s.tenant_id and r.company_id = s.company_id and r.settlement_id = s.id)
                       ), 0)
                  from actionfinance.financial_title t
                 where t.tenant_id = ? and t.company_id = ? and t.status = 'OPEN'
                """,
                (rs, n) -> new OpenTitle(
                        rs.getString(1),
                        rs.getString(2),
                        rs.getDate(3) == null ? null : rs.getDate(3).toLocalDate(),
                        rs.getLong(4)),
                scope.tenantId(),
                scope.companyId());
        Integer review = jdbc.queryForObject(
                """
                select count(*) from actionfinance.statement_occurrence
                 where tenant_id = ? and company_id = ? and consolidation = 'IN_REVIEW'
                """,
                Integer.class,
                scope.tenantId(),
                scope.companyId());
        Integer statementLines = jdbc.queryForObject(
                """
                select count(*) from actionfinance.statement_line
                 where tenant_id = ? and company_id = ? and import_status = 'ACTIVE'
                """,
                Integer.class,
                scope.tenantId(),
                scope.companyId());
        Integer pending = jdbc.queryForObject(
                """
                select count(*) from actionfinance.statement_line l
                 where l.tenant_id = ? and l.company_id = ?
                   and l.import_status = 'ACTIVE' and l.net_absent = false
                   and not exists (
                     select 1 from actionfinance.statement_book_allocation a
                      where a.tenant_id = l.tenant_id and a.company_id = l.company_id
                        and a.line_id = l.id and a.status = 'ACTIVE')
                """,
                Integer.class,
                scope.tenantId(),
                scope.companyId());
        Instant lastSync = jdbc.query(
                """
                select max(finished_at) from actionfinance.pay_receipt_sync_run
                 where tenant_id = ? and company_id = ? and status in ('SUCCESS', 'EMPTY', 'PARTIAL')
                """,
                (rs, n) -> rs.getTimestamp(1) == null ? null : rs.getTimestamp(1).toInstant(),
                scope.tenantId(),
                scope.companyId()).stream().findFirst().orElse(null);
        Instant lastStatement = jdbc.query(
                """
                select max(confirmed_at) from actionfinance.statement_batch
                 where tenant_id = ? and company_id = ? and status = 'CONFIRMED'
                """,
                (rs, n) -> rs.getTimestamp(1) == null ? null : rs.getTimestamp(1).toInstant(),
                scope.tenantId(),
                scope.companyId()).stream().findFirst().orElse(null);
        return new OverviewFacts(
                pay,
                sales,
                fees == null ? new FeeReading(0, 0, 0) : fees,
                expenses,
                cash,
                titles,
                review == null ? 0 : review,
                pending == null ? 0 : pending,
                statementLines == null ? 0 : statementLines,
                lastSync,
                lastStatement,
                accountName);
    }

    private record CoveredPosition(int count, long minor) {}
}
