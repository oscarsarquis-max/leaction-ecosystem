package br.com.actionfinance.application.treasury;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.CompanyAccessService;
import br.com.actionfinance.application.identity.FinancePermissions;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.sql.Date;
import java.time.Clock;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class TreasuryService {

    static final ZoneId ZONE = ZoneId.of("America/Sao_Paulo");
    private static final String RESIDUAL =
            """
            (t.amount_minor - coalesce((
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
            ), 0))
            """;

    private final JdbcTemplate jdbc;
    private final CompanyAccessService access;
    private final Clock clock;

    public TreasuryService(JdbcTemplate jdbc, CompanyAccessService access, Clock clock) {
        this.jdbc = jdbc;
        this.access = access;
        this.clock = clock;
    }

    public Map<String, Object> summary(ApplicationPrincipal principal, UUID companyId, LocalDate from, LocalDate to) {
        LocalDate today = LocalDate.now(clock.withZone(ZONE));
        LocalDate start = from == null ? today.withDayOfMonth(1) : from;
        LocalDate end = to == null ? today : to;
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("businessDate", today);
        body.put("zone", ZONE.getId());
        body.put("periodFrom", start);
        body.put("periodTo", end);
        body.put("note", "Estas bases não se somam. Vencido já está dentro do em aberto.");
        body.put("scopes", Map.of(
                "obligations", "Situação atual dos títulos em aberto. Não usa o período do realizado.",
                "realized", "Baixas válidas com data efetiva dentro do período mostrado.",
                "conference", "Extrato dos lotes confirmados, sem o recorte do período do realizado.",
                "position", "Posição na data de referência. Não é o início do período nem o total da empresa."));
        if (allowed(principal, companyId, FinancePermissions.TITLES_READ)) {
            AuthorizedScope scope = access.requireWritable(principal, companyId, FinancePermissions.TITLES_READ);
            body.put("obligations", obligations(scope, today));
            body.put("realized", realized(scope, start, end));
        } else {
            body.put("obligations", Map.of("available", false));
            body.put("realized", Map.of("available", false));
        }
        if (allowed(principal, companyId, FinancePermissions.ACCOUNTS_READ)) {
            AuthorizedScope scope = access.requireWritable(principal, companyId, FinancePermissions.ACCOUNTS_READ);
            body.put("conference", conference(scope));
            body.put("position", position(scope, today));
        } else {
            body.put("conference", Map.of("available", false));
            body.put("position", Map.of("available", false));
        }
        return body;
    }

    public Map<String, Object> agenda(
            ApplicationPrincipal principal, UUID companyId, String bucket, String direction, int page, int size) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, FinancePermissions.TITLES_READ);
        LocalDate today = LocalDate.now(clock.withZone(ZONE));
        String notice = null;
        String chosen = bucket == null || bucket.isBlank() ? "OVERDUE" : bucket.trim();
        if (!Set.of("OVERDUE", "TODAY", "NEXT_7", "NEXT_30", "UNDATED").contains(chosen)) {
            notice = "A faixa informada não existe. A agenda abriu em Vencidos.";
            chosen = "OVERDUE";
        }
        String chosenDirection = "";
        if (direction != null && !direction.isBlank()) {
            if ("RECEIVABLE".equals(direction) || "PAYABLE".equals(direction)) {
                chosenDirection = direction;
            } else {
                String directionNotice = "A direção informada não existe. A agenda mostra recebimentos e pagamentos.";
                notice = notice == null ? directionNotice : notice + " " + directionNotice;
            }
        }
        int safePage = Math.max(page, 0);
        int safeSize = Math.min(Math.max(size, 1), 50);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("businessDate", today);
        body.put("zone", ZONE.getId());
        body.put("bucket", chosen);
        body.put("direction", chosenDirection.isEmpty() ? "ALL" : chosenDirection);
        body.put("notice", notice);
        body.put("accountNote", "A agenda é da empresa. Conta ainda não definida nos compromissos em aberto.");
        body.put("buckets", buckets(scope, today, chosenDirection));
        body.put("items", items(scope, today, chosen, chosenDirection, safePage, safeSize));
        body.put("page", safePage);
        body.put("size", safeSize);
        return body;
    }

    public Map<String, Object> calendar(
            ApplicationPrincipal principal,
            UUID companyId,
            String month,
            String direction,
            String day,
            String focus,
            int page,
            int size) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, FinancePermissions.TITLES_READ);
        LocalDate today = LocalDate.now(clock.withZone(ZONE));
        String notice = null;
        YearMonth chosen = YearMonth.from(today);
        if (month != null && !month.isBlank()) {
            try {
                chosen = YearMonth.parse(month.trim());
            } catch (RuntimeException exception) {
                notice = "O mês informado não existe. A agenda abriu no mês atual.";
            }
        }
        String chosenDirection = "";
        if (direction != null && !direction.isBlank()) {
            if ("RECEIVABLE".equals(direction) || "PAYABLE".equals(direction)) {
                chosenDirection = direction;
            } else {
                String directionNotice = "A direção informada não existe. A agenda mostra recebimentos e pagamentos.";
                notice = notice == null ? directionNotice : notice + " " + directionNotice;
            }
        }
        String chosenFocus = focus == null || focus.isBlank() ? "DAY" : focus.trim();
        if (!Set.of("DAY", "UNDATED", "OVERDUE_OUTSIDE").contains(chosenFocus)) {
            notice = appendNotice(notice, "O painel informado não existe. A agenda mostra o dia selecionado.");
            chosenFocus = "DAY";
        }
        LocalDate monthStart = chosen.atDay(1);
        LocalDate monthEnd = chosen.atEndOfMonth();
        LocalDate gridStart = monthStart.minusDays(monthStart.getDayOfWeek().getValue() - 1L);
        long tail = monthEnd.getDayOfWeek() == DayOfWeek.SUNDAY ? 0 : 7L - monthEnd.getDayOfWeek().getValue();
        LocalDate gridEnd = monthEnd.plusDays(tail);
        LocalDate selected = monthStart;
        if (day != null && !day.isBlank()) {
            try {
                LocalDate parsed = LocalDate.parse(day.trim());
                if (!parsed.isBefore(gridStart) && !parsed.isAfter(gridEnd)) {
                    selected = parsed;
                } else {
                    notice = appendNotice(notice, "A data informada está fora da grade deste mês.");
                    selected = !today.isBefore(monthStart) && !today.isAfter(monthEnd) ? today : monthStart;
                }
            } catch (RuntimeException exception) {
                notice = appendNotice(notice, "A data informada não existe.");
            }
        } else if (!today.isBefore(monthStart) && !today.isAfter(monthEnd)) {
            selected = today;
        }
        int safePage = Math.max(page, 0);
        int safeSize = Math.min(Math.max(size, 1), 50);
        List<Map<String, Object>> days = calendarDays(scope, today, gridStart, gridEnd, monthStart, monthEnd, chosenDirection);
        Map<String, Object> monthTotals = monthTotals(days);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("businessDate", today);
        body.put("zone", ZONE.getId());
        body.put("currency", "BRL");
        body.put("month", chosen.toString());
        body.put("monthLabel", monthLabel(chosen));
        body.put("monthFrom", monthStart);
        body.put("monthTo", monthEnd);
        body.put("gridFrom", gridStart);
        body.put("gridTo", gridEnd);
        body.put("coverage", "MONTH_AND_ADJACENT_DAYS");
        body.put("monthTotalScope", "Somente vencimentos do mês consultado. Os dias vizinhos da grade foram consultados e não entram neste total.");
        body.put("direction", chosenDirection.isEmpty() ? "ALL" : chosenDirection);
        body.put("selectedDay", "DAY".equals(chosenFocus) ? selected : null);
        body.put("focus", chosenFocus);
        body.put("notice", notice);
        body.put("days", days);
        body.put("monthTotals", monthTotals);
        body.put("differenceMeaning", "Diferença prevista entre a receber e a pagar no mês. Não é saldo bancário nem posição da conta.");
        body.put("undated", undated(scope, chosenDirection));
        body.put("undatedNote", "Título em aberto neste domínio exige vencimento. Compromisso sem data não é colocado em hoje.");
        body.put("overdueOutside", overdueOutside(scope, today, monthStart, monthEnd, chosenDirection));
        body.put("items", calendarItems(scope, today, chosenFocus, selected, monthStart, monthEnd, chosenDirection, safePage, safeSize));
        body.put("page", safePage);
        body.put("size", safeSize);
        body.put("accountNote", "A agenda é da empresa. Conta ainda não definida nos compromissos em aberto.");
        return body;
    }

    private List<Map<String, Object>> calendarDays(
            AuthorizedScope scope, LocalDate today, LocalDate gridStart, LocalDate gridEnd,
            LocalDate monthStart, LocalDate monthEnd, String direction) {
        Map<LocalDate, Map<String, Object>> found = new java.util.HashMap<>();
        jdbc.query(
                """
                select t.due_date,
                  count(*) filter (where t.direction = 'RECEIVABLE') as in_count,
                  coalesce(sum(%s) filter (where t.direction = 'RECEIVABLE'), 0) as in_amount,
                  count(*) filter (where t.direction = 'PAYABLE') as out_count,
                  coalesce(sum(%s) filter (where t.direction = 'PAYABLE'), 0) as out_amount
                  from actionfinance.financial_title t
                 where t.tenant_id = ? and t.company_id = ? and t.status = 'OPEN' and t.currency = 'BRL'
                   and t.due_date >= ? and t.due_date <= ?
                   and %s > 0
                   %s
                 group by t.due_date
                """.formatted(RESIDUAL, RESIDUAL, RESIDUAL, directionSql(direction)),
                (rs, n) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    LocalDate due = rs.getDate("due_date").toLocalDate();
                    row.put("receivableCount", number(rs.getObject("in_count")));
                    row.put("receivableMinor", minor(rs.getObject("in_amount")));
                    row.put("payableCount", number(rs.getObject("out_count")));
                    row.put("payableMinor", minor(rs.getObject("out_amount")));
                    found.put(due, row);
                    return null;
                },
                scope.tenantId(), scope.companyId(), Date.valueOf(gridStart), Date.valueOf(gridEnd));
        List<Map<String, Object>> days = new ArrayList<>();
        for (LocalDate cursor = gridStart; !cursor.isAfter(gridEnd); cursor = cursor.plusDays(1)) {
            Map<String, Object> row = new LinkedHashMap<>();
            Map<String, Object> hit = found.get(cursor);
            row.put("date", cursor);
            row.put("inMonth", !cursor.isBefore(monthStart) && !cursor.isAfter(monthEnd));
            row.put("today", cursor.equals(today));
            row.put("overdue", cursor.isBefore(today));
            row.put("receivableCount", hit == null ? 0 : hit.get("receivableCount"));
            row.put("receivableMinor", hit == null ? "0" : hit.get("receivableMinor"));
            row.put("payableCount", hit == null ? 0 : hit.get("payableCount"));
            row.put("payableMinor", hit == null ? "0" : hit.get("payableMinor"));
            row.put("collected", true);
            days.add(row);
        }
        return days;
    }

    private Map<String, Object> monthTotals(List<Map<String, Object>> days) {
        BigDecimal receivable = BigDecimal.ZERO;
        BigDecimal payable = BigDecimal.ZERO;
        long receivableCount = 0;
        long payableCount = 0;
        for (Map<String, Object> day : days) {
            if (!Boolean.TRUE.equals(day.get("inMonth"))) {
                continue;
            }
            receivable = receivable.add(new BigDecimal(String.valueOf(day.get("receivableMinor"))));
            payable = payable.add(new BigDecimal(String.valueOf(day.get("payableMinor"))));
            receivableCount += number(day.get("receivableCount"));
            payableCount += number(day.get("payableCount"));
        }
        Map<String, Object> totals = new LinkedHashMap<>();
        totals.put("receivableCount", receivableCount);
        totals.put("receivableMinor", receivable.toPlainString());
        totals.put("payableCount", payableCount);
        totals.put("payableMinor", payable.toPlainString());
        totals.put("differenceMinor", receivable.subtract(payable).toPlainString());
        return totals;
    }

    private Map<String, Object> undated(AuthorizedScope scope, String direction) {
        return oneSide(
                """
                select
                  count(*) filter (where t.direction = 'RECEIVABLE') as in_count,
                  coalesce(sum(%s) filter (where t.direction = 'RECEIVABLE'), 0) as in_amount,
                  count(*) filter (where t.direction = 'PAYABLE') as out_count,
                  coalesce(sum(%s) filter (where t.direction = 'PAYABLE'), 0) as out_amount
                  from actionfinance.financial_title t
                 where t.tenant_id = ? and t.company_id = ? and t.status = 'OPEN' and t.currency = 'BRL'
                   and t.due_date is null and %s > 0
                   %s
                """.formatted(RESIDUAL, RESIDUAL, RESIDUAL, directionSql(direction)),
                scope.tenantId(), scope.companyId());
    }

    private Map<String, Object> overdueOutside(
            AuthorizedScope scope, LocalDate today, LocalDate monthStart, LocalDate monthEnd, String direction) {
        return oneSide(
                """
                select
                  count(*) filter (where t.direction = 'RECEIVABLE') as in_count,
                  coalesce(sum(%s) filter (where t.direction = 'RECEIVABLE'), 0) as in_amount,
                  count(*) filter (where t.direction = 'PAYABLE') as out_count,
                  coalesce(sum(%s) filter (where t.direction = 'PAYABLE'), 0) as out_amount
                  from actionfinance.financial_title t
                 where t.tenant_id = ? and t.company_id = ? and t.status = 'OPEN' and t.currency = 'BRL'
                   and t.due_date < ? and (t.due_date < ? or t.due_date > ?)
                   and %s > 0
                   %s
                """.formatted(RESIDUAL, RESIDUAL, RESIDUAL, directionSql(direction)),
                scope.tenantId(), scope.companyId(), Date.valueOf(today), Date.valueOf(monthStart), Date.valueOf(monthEnd));
    }

    private Map<String, Object> oneSide(String sql, Object... args) {
        Map<String, Object> row = jdbc.queryForMap(sql, args);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("receivableCount", number(row.get("in_count")));
        body.put("receivableMinor", minor(row.get("in_amount")));
        body.put("payableCount", number(row.get("out_count")));
        body.put("payableMinor", minor(row.get("out_amount")));
        return body;
    }

    private Map<String, Object> calendarItems(
            AuthorizedScope scope, LocalDate today, String focus, LocalDate selected,
            LocalDate monthStart, LocalDate monthEnd, String direction, int page, int size) {
        String window;
        List<Object> args = new ArrayList<>();
        args.add(scope.tenantId());
        args.add(scope.companyId());
        if ("UNDATED".equals(focus)) {
            window = " and t.due_date is null ";
        } else if ("OVERDUE_OUTSIDE".equals(focus)) {
            window = " and t.due_date < ? and (t.due_date < ? or t.due_date > ?) ";
            args.add(Date.valueOf(today));
            args.add(Date.valueOf(monthStart));
            args.add(Date.valueOf(monthEnd));
        } else {
            window = " and t.due_date = ? ";
            args.add(Date.valueOf(selected));
        }
        String directionFilter = directionSql(direction);
        Long total = jdbc.queryForObject(
                """
                select count(*) from actionfinance.financial_title t
                 where t.tenant_id = ? and t.company_id = ? and t.status = 'OPEN' and t.currency = 'BRL'
                   and %s > 0
                   %s
                   %s
                """.formatted(RESIDUAL, window, directionFilter),
                Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(size);
        pageArgs.add(page * size);
        List<Map<String, Object>> items = jdbc.query(
                """
                select t.id, t.direction, t.description, t.due_date, t.amount_minor, cp.name as counterparty,
                       %s as residual
                  from actionfinance.financial_title t
                  left join actionfinance.counterparty cp
                    on cp.tenant_id = t.tenant_id and cp.company_id = t.company_id and cp.id = t.counterparty_id
                 where t.tenant_id = ? and t.company_id = ? and t.status = 'OPEN' and t.currency = 'BRL'
                   and %s > 0
                   %s
                   %s
                 order by t.due_date asc nulls last, t.direction, t.id
                 limit ? offset ?
                """.formatted(RESIDUAL, RESIDUAL, window, directionFilter),
                (rs, n) -> {
                    BigDecimal residual = rs.getBigDecimal("residual");
                    BigDecimal amount = rs.getBigDecimal("amount_minor");
                    String itemDirection = rs.getString("direction");
                    boolean partial = amount != null && residual.compareTo(amount) < 0;
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("id", rs.getObject("id", UUID.class));
                    item.put("direction", itemDirection);
                    item.put("description", rs.getString("description"));
                    item.put("dueDate", rs.getDate("due_date") == null ? null : rs.getDate("due_date").toLocalDate());
                    item.put("counterparty", rs.getString("counterparty"));
                    item.put("residualMinor", residual.toPlainString());
                    item.put("partial", partial);
                    item.put("partialLabel", partial
                            ? ("PAYABLE".equals(itemDirection) ? "Parcialmente pago" : "Parcialmente recebido")
                            : null);
                    item.put("overdue", rs.getDate("due_date") != null && rs.getDate("due_date").toLocalDate().isBefore(today));
                    item.put("account", "Conta ainda não definida");
                    return item;
                },
                pageArgs.toArray());
        Map<String, Object> pageBody = new LinkedHashMap<>();
        pageBody.put("total", total == null ? 0 : total);
        pageBody.put("items", items);
        return pageBody;
    }

    private static String appendNotice(String notice, String next) {
        return notice == null ? next : notice + " " + next;
    }

    private static String monthLabel(YearMonth month) {
        String[] names = {
                "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
        };
        return names[month.getMonthValue() - 1] + " de " + month.getYear();
    }

    private boolean allowed(ApplicationPrincipal principal, UUID companyId, String permission) {
        try {
            access.requirePermission(principal, companyId, permission);
            return true;
        } catch (SecurityException exception) {
            return false;
        }
    }

    private Map<String, Object> obligations(AuthorizedScope scope, LocalDate today) {
        Map<String, Object> row = jdbc.queryForMap(
                """
                select
                  coalesce(sum(%s) filter (where t.direction = 'RECEIVABLE' and t.status = 'OPEN' and %s > 0), 0) as in_open,
                  count(*) filter (where t.direction = 'RECEIVABLE' and t.status = 'OPEN' and %s > 0) as in_open_count,
                  coalesce(sum(%s) filter (where t.direction = 'RECEIVABLE' and t.status = 'OPEN' and t.due_date < ? and %s > 0), 0) as in_overdue,
                  count(*) filter (where t.direction = 'RECEIVABLE' and t.status = 'OPEN' and t.due_date < ? and %s > 0) as in_overdue_count,
                  coalesce(sum(%s) filter (where t.direction = 'PAYABLE' and t.status = 'OPEN' and %s > 0), 0) as out_open,
                  count(*) filter (where t.direction = 'PAYABLE' and t.status = 'OPEN' and %s > 0) as out_open_count,
                  coalesce(sum(%s) filter (where t.direction = 'PAYABLE' and t.status = 'OPEN' and t.due_date < ? and %s > 0), 0) as out_overdue,
                  count(*) filter (where t.direction = 'PAYABLE' and t.status = 'OPEN' and t.due_date < ? and %s > 0) as out_overdue_count,
                  count(*) filter (where t.status = 'DRAFT') as draft_count
                  from actionfinance.financial_title t
                 where t.tenant_id = ? and t.company_id = ? and t.currency = 'BRL'
                """.formatted(RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL),
                Date.valueOf(today), Date.valueOf(today), Date.valueOf(today), Date.valueOf(today),
                scope.tenantId(), scope.companyId());
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("available", true);
        body.put("currency", "BRL");
        body.put("receivableOpenMinor", minor(row.get("in_open")));
        body.put("receivableOpenCount", number(row.get("in_open_count")));
        body.put("receivableOverdueMinor", minor(row.get("in_overdue")));
        body.put("receivableOverdueCount", number(row.get("in_overdue_count")));
        body.put("payableOpenMinor", minor(row.get("out_open")));
        body.put("payableOpenCount", number(row.get("out_open_count")));
        body.put("payableOverdueMinor", minor(row.get("out_overdue")));
        body.put("payableOverdueCount", number(row.get("out_overdue_count")));
        body.put("draftCount", number(row.get("draft_count")));
        body.put("draftNote", "Rascunhos entram só como quantidade. O valor deles não está no em aberto.");
        return body;
    }

    private Map<String, Object> realized(AuthorizedScope scope, LocalDate from, LocalDate to) {
        Map<String, Object> row = jdbc.queryForMap(
                """
                select
                  coalesce(sum(s.amount_minor) filter (where s.direction = 'RECEIVABLE'), 0) as received,
                  count(*) filter (where s.direction = 'RECEIVABLE') as received_count,
                  coalesce(sum(s.amount_minor) filter (where s.direction = 'PAYABLE'), 0) as paid,
                  count(*) filter (where s.direction = 'PAYABLE') as paid_count
                  from actionfinance.settlement s
                 where s.tenant_id = ? and s.company_id = ? and s.currency = 'BRL'
                   and s.effective_date >= ? and s.effective_date <= ?
                   and not exists (
                     select 1 from actionfinance.settlement_reversal r
                      where r.tenant_id = s.tenant_id and r.company_id = s.company_id and r.settlement_id = s.id
                   )
                """,
                scope.tenantId(), scope.companyId(), Date.valueOf(from), Date.valueOf(to));
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("available", true);
        body.put("receivedMinor", minor(row.get("received")));
        body.put("receivedCount", number(row.get("received_count")));
        body.put("paidMinor", minor(row.get("paid")));
        body.put("paidCount", number(row.get("paid_count")));
        body.put("meaning", "Baixas válidas no Finance. Não é confirmação da origem nem extrato.");
        return body;
    }

    private Map<String, Object> conference(AuthorizedScope scope) {
        Map<String, Object> row = jdbc.queryForMap(
                """
                with lined as (
                  select l.net_minor,
                         (l.import_status = 'ACTIVE' and l.balance_effect = 'AFFECTS' and l.availability = 'RELEASED'
                           and l.net_absent = false and l.currency_assumed = false
                           and l.direction in ('IN', 'OUT') and l.net_minor is not null) as eligible,
                         coalesce((select abs(sum(a.movement_sign * a.allocated_minor))
                                     from actionfinance.statement_book_allocation a
                                    where a.line_id = l.id and a.status = 'ACTIVE'), 0) as book_minor,
                         coalesce((select bool_or(
                                      (select coalesce(sum(a2.allocated_minor), 0)
                                         from actionfinance.statement_book_allocation a2
                                        where a2.movement_id = a.movement_id and a2.status = 'ACTIVE')
                                      < abs(m.signed_amount_minor))
                                     from actionfinance.statement_book_allocation a
                                     join actionfinance.cash_movement m on m.id = a.movement_id
                                    where a.line_id = l.id and a.status = 'ACTIVE'), false) as book_residual
                    from actionfinance.statement_line l
                   where l.tenant_id = ? and l.company_id = ?
                )
                select
                  count(*) filter (where eligible) as eligible,
                  count(*) filter (where eligible and book_minor > 0 and book_minor < net_minor) as partial,
                  count(*) filter (where eligible and book_minor > 0
                    and not (book_minor < net_minor)
                    and not (book_minor = net_minor and not book_residual)) as divergent
                  from lined
                """,
                scope.tenantId(), scope.companyId());
        Integer review = jdbc.queryForObject(
                """
                select count(*)
                  from actionfinance.statement_occurrence o
                  join actionfinance.statement_batch b
                    on b.tenant_id = o.tenant_id and b.company_id = o.company_id and b.id = o.batch_id
                 where o.tenant_id = ? and o.company_id = ?
                   and o.consolidation = 'IN_REVIEW' and b.status = 'CONFIRMED'
                """,
                Integer.class, scope.tenantId(), scope.companyId());
        List<Map<String, Object>> batches = jdbc.query(
                """
                select b.id, b.account_id, b.file_name, count(*) as occurrence_count
                  from actionfinance.statement_occurrence o
                  join actionfinance.statement_batch b
                    on b.tenant_id = o.tenant_id and b.company_id = o.company_id and b.id = o.batch_id
                 where o.tenant_id = ? and o.company_id = ?
                   and o.consolidation = 'IN_REVIEW' and b.status = 'CONFIRMED'
                 group by b.id, b.account_id, b.file_name
                 order by b.file_name
                """,
                (rs, n) -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("batchId", rs.getObject("id", UUID.class));
                    item.put("accountId", rs.getObject("account_id", UUID.class));
                    item.put("fileName", rs.getString("file_name"));
                    item.put("occurrenceCount", rs.getLong("occurrence_count"));
                    return item;
                },
                scope.tenantId(), scope.companyId());
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("available", true);
        body.put("eligibleCount", number(row.get("eligible")));
        body.put("partialCount", number(row.get("partial")));
        body.put("divergentCount", number(row.get("divergent")));
        body.put("reviewCount", review == null ? 0 : review);
        body.put("reviewUnit", "OCCURRENCE");
        body.put("reviewNote", "Cada linha preservada do arquivo conta uma vez. Repetições documentais não são eventos únicos. Lotes retirados ficam no histórico e não entram neste número.");
        body.put("reviewBatches", batches);
        body.put("meaning", "Parcial e diferença usam a mesma situação da fila de conciliação do livro. Referência comercial não entra nessa conta. Ocorrência em revisão não é evento consolidado.");
        return body;
    }

    private Map<String, Object> position(AuthorizedScope scope, LocalDate today) {
        List<Map<String, Object>> accounts = jdbc.query(
                """
                select a.id, a.name, a.currency, a.active,
                       (select m.effective_date from actionfinance.cash_movement m
                         where m.tenant_id = a.tenant_id and m.company_id = a.company_id
                           and m.account_id = a.id and m.kind = 'OPENING') as opening_on,
                       coalesce((
                         select sum(m.signed_amount_minor) from actionfinance.cash_movement m
                          where m.tenant_id = a.tenant_id and m.company_id = a.company_id
                            and m.account_id = a.id and m.effective_date <= ?
                       ), 0) as balance_minor
                  from actionfinance.financial_account a
                 where a.tenant_id = ? and a.company_id = ?
                 order by a.active desc, a.name
                """,
                (rs, n) -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("name", rs.getString("name"));
                    item.put("currency", rs.getString("currency"));
                    item.put("active", rs.getBoolean("active"));
                    Date opening = rs.getDate("opening_on");
                    item.put("openingOn", opening == null ? null : opening.toLocalDate());
                    item.put("balanceMinor", rs.getBigDecimal("balance_minor"));
                    return item;
                },
                Date.valueOf(today), scope.tenantId(), scope.companyId());
        BigDecimal activeKnown = BigDecimal.ZERO;
        int covered = 0;
        Map<String, List<Map<String, Object>>> grouped = new LinkedHashMap<>();
        for (String reason : List.of("MOEDA", "SEM_SALDO_INICIAL", "SALDO_INICIAL_POSTERIOR", "INATIVA")) {
            grouped.put(reason, new ArrayList<>());
        }
        for (Map<String, Object> account : accounts) {
            String name = String.valueOf(account.get("name"));
            String currency = String.valueOf(account.get("currency"));
            boolean active = Boolean.TRUE.equals(account.get("active"));
            LocalDate openingOn = (LocalDate) account.get("openingOn");
            BigDecimal balance = (BigDecimal) account.get("balanceMinor");
            if (!"BRL".equals(currency)) {
                grouped.get("MOEDA").add(exclusion(name, "Moeda diferente de real. Não entra nesta soma."));
                continue;
            }
            if (openingOn == null) {
                grouped.get("SEM_SALDO_INICIAL").add(exclusion(name, active
                        ? "Conta ativa sem saldo inicial informado."
                        : "Conta inativa sem saldo inicial informado."));
                continue;
            }
            if (openingOn.isAfter(today)) {
                grouped.get("SALDO_INICIAL_POSTERIOR").add(exclusion(
                        name, "O saldo inicial vale a partir de " + openingOn + " e não compõe esta data."));
                continue;
            }
            if (!active) {
                Map<String, Object> item = exclusion(name, "Conta inativa. O valor permanece visível e fica fora da soma das contas ativas.");
                item.put("knownMinor", balance.toPlainString());
                grouped.get("INATIVA").add(item);
                continue;
            }
            activeKnown = activeKnown.add(balance);
            covered++;
        }
        List<Map<String, Object>> exclusions = new ArrayList<>();
        exclusions.add(exclusionGroup("MOEDA", "Outra moeda", grouped.get("MOEDA")));
        exclusions.add(exclusionGroup("SEM_SALDO_INICIAL", "Sem saldo inicial", grouped.get("SEM_SALDO_INICIAL")));
        exclusions.add(exclusionGroup("SALDO_INICIAL_POSTERIOR", "Saldo inicial posterior à data", grouped.get("SALDO_INICIAL_POSTERIOR")));
        exclusions.add(exclusionGroup("INATIVA", "Conta inativa com posição conhecida", grouped.get("INATIVA")));
        exclusions.removeIf(group -> ((Number) group.get("count")).intValue() == 0);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("available", true);
        body.put("asOf", today);
        body.put("known", covered > 0);
        body.put("label", covered > 0 ? "Posição das contas ativas apuradas" : "Posição não apurada");
        body.put("currency", "BRL");
        if (covered > 0) {
            body.put("knownMinor", activeKnown.toPlainString());
        }
        body.put("coveredAccounts", covered);
        body.put("accountCount", accounts.size());
        body.put("exclusions", exclusions);
        body.put("source", "Livro do Finance até esta data, só com saldo inicial já aplicável e moeda real.");
        body.put("limit", "É a soma das contas ativas apuradas. Não é o saldo total da empresa nem a posição no início do período. Conta inativa com valor continua listada à parte.");
        body.put("guidance", covered > 0 ? null : "Nenhuma conta ativa tem saldo inicial aplicável nesta data. Consulte as contas.");
        return body;
    }

    private static Map<String, Object> exclusion(String name, String detail) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("name", name);
        item.put("detail", detail);
        return item;
    }

    private static Map<String, Object> exclusionGroup(String reason, String label, List<Map<String, Object>> accounts) {
        Map<String, Object> group = new LinkedHashMap<>();
        group.put("reason", reason);
        group.put("label", label);
        group.put("count", accounts.size());
        group.put("accounts", accounts);
        return group;
    }

    private List<Map<String, Object>> buckets(AuthorizedScope scope, LocalDate today, String direction) {
        String directionSql = directionSql(direction);
        Map<String, Object> row = jdbc.queryForMap(
                """
                select
                  count(*) filter (where t.due_date < ?) as overdue_count,
                  coalesce(sum(%s) filter (where t.due_date < ?), 0) as overdue_amount,
                  count(*) filter (where t.due_date = ?) as today_count,
                  coalesce(sum(%s) filter (where t.due_date = ?), 0) as today_amount,
                  count(*) filter (where t.due_date > ? and t.due_date <= ?) as week_count,
                  coalesce(sum(%s) filter (where t.due_date > ? and t.due_date <= ?), 0) as week_amount,
                  count(*) filter (where t.due_date > ? and t.due_date <= ?) as month_count,
                  coalesce(sum(%s) filter (where t.due_date > ? and t.due_date <= ?), 0) as month_amount,
                  count(*) filter (where t.due_date is null) as undated_count,
                  coalesce(sum(%s) filter (where t.due_date is null), 0) as undated_amount
                  from actionfinance.financial_title t
                 where t.tenant_id = ? and t.company_id = ? and t.status = 'OPEN' and t.currency = 'BRL'
                   and %s > 0
                   %s
                """.formatted(RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, RESIDUAL, directionSql),
                Date.valueOf(today), Date.valueOf(today),
                Date.valueOf(today), Date.valueOf(today),
                Date.valueOf(today), Date.valueOf(today.plusDays(7)), Date.valueOf(today), Date.valueOf(today.plusDays(7)),
                Date.valueOf(today.plusDays(7)), Date.valueOf(today.plusDays(30)), Date.valueOf(today.plusDays(7)), Date.valueOf(today.plusDays(30)),
                scope.tenantId(), scope.companyId());
        return List.of(
                bucket("OVERDUE", "Vencidos", row, "overdue"),
                bucket("TODAY", "Hoje", row, "today"),
                bucket("NEXT_7", "Próximos 7 dias", row, "week"),
                bucket("NEXT_30", "Do 8º ao 30º dia", row, "month"),
                bucket("UNDATED", "Sem data", row, "undated"));
    }

    private Map<String, Object> items(
            AuthorizedScope scope, LocalDate today, String bucket, String direction, int page, int size) {
        String window = switch (bucket) {
            case "TODAY" -> " and t.due_date = ? ";
            case "NEXT_7" -> " and t.due_date > ? and t.due_date <= ? ";
            case "NEXT_30" -> " and t.due_date > ? and t.due_date <= ? ";
            case "UNDATED" -> " and t.due_date is null ";
            default -> " and t.due_date < ? ";
        };
        List<Object> args = new ArrayList<>();
        args.add(scope.tenantId());
        args.add(scope.companyId());
        if ("NEXT_7".equals(bucket)) {
            args.add(Date.valueOf(today));
            args.add(Date.valueOf(today.plusDays(7)));
        } else if ("NEXT_30".equals(bucket)) {
            args.add(Date.valueOf(today.plusDays(7)));
            args.add(Date.valueOf(today.plusDays(30)));
        } else if (!"UNDATED".equals(bucket)) {
            args.add(Date.valueOf(today));
        }
        String directionSql = directionSql(direction);
        Long total = jdbc.queryForObject(
                """
                select count(*) from actionfinance.financial_title t
                 where t.tenant_id = ? and t.company_id = ? and t.status = 'OPEN' and t.currency = 'BRL'
                   and %s > 0
                   %s
                   %s
                """.formatted(RESIDUAL, window, directionSql),
                Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(size);
        pageArgs.add(page * size);
        List<Map<String, Object>> items = jdbc.query(
                """
                select t.id, t.direction, t.description, t.due_date, t.reference, cp.name as counterparty,
                       %s as residual
                  from actionfinance.financial_title t
                  left join actionfinance.counterparty cp
                    on cp.tenant_id = t.tenant_id and cp.company_id = t.company_id and cp.id = t.counterparty_id
                 where t.tenant_id = ? and t.company_id = ? and t.status = 'OPEN' and t.currency = 'BRL'
                   and %s > 0
                   %s
                   %s
                 order by t.due_date asc nulls last, t.id
                 limit ? offset ?
                """.formatted(RESIDUAL, RESIDUAL, window, directionSql),
                (rs, n) -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("id", rs.getObject("id", UUID.class));
                    item.put("direction", rs.getString("direction"));
                    item.put("description", rs.getString("description"));
                    item.put("dueDate", rs.getDate("due_date") == null ? null : rs.getDate("due_date").toLocalDate());
                    item.put("reference", rs.getString("reference"));
                    item.put("counterparty", rs.getString("counterparty"));
                    item.put("residualMinor", rs.getBigDecimal("residual").toPlainString());
                    item.put("account", "Conta ainda não definida");
                    return item;
                },
                pageArgs.toArray());
        Map<String, Object> pageBody = new LinkedHashMap<>();
        pageBody.put("total", total == null ? 0 : total);
        pageBody.put("items", items);
        return pageBody;
    }

    private static Map<String, Object> bucket(String id, String label, Map<String, Object> row, String prefix) {
        Map<String, Object> bucket = new LinkedHashMap<>();
        bucket.put("id", id);
        bucket.put("label", label);
        bucket.put("count", number(row.get(prefix + "_count")));
        bucket.put("residualMinor", minor(row.get(prefix + "_amount")));
        return bucket;
    }

    private static String directionSql(String direction) {
        if ("RECEIVABLE".equals(direction)) {
            return " and t.direction = 'RECEIVABLE' ";
        }
        if ("PAYABLE".equals(direction)) {
            return " and t.direction = 'PAYABLE' ";
        }
        return "";
    }

    private static String minor(Object value) {
        if (value == null) {
            return "0";
        }
        if (value instanceof BigDecimal decimal) {
            return decimal.toPlainString();
        }
        return new BigDecimal(String.valueOf(value)).toPlainString();
    }

    private static long number(Object value) {
        if (value == null) {
            return 0;
        }
        if (value instanceof Number numeric) {
            return numeric.longValue();
        }
        return Long.parseLong(String.valueOf(value));
    }
}
