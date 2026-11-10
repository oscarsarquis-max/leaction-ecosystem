package br.com.actionfinance.application.overview;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.CompanyAccessService;
import br.com.actionfinance.application.identity.FinancePermissions;
import br.com.actionfinance.application.overview.OverviewFacts.CashReading;
import br.com.actionfinance.application.overview.OverviewFacts.CategoryAmount;
import br.com.actionfinance.application.overview.OverviewFacts.MethodAmount;
import br.com.actionfinance.application.overview.OverviewFacts.OpenTitle;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@Service
public class OverviewService {

    static final ZoneId ZONE = ZoneId.of("America/Sao_Paulo");
    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("dd/MM");

    private final CompanyAccessService companies;
    private final OverviewStore store;
    private final Clock clock;

    public OverviewService(CompanyAccessService companies, OverviewStore store, Clock clock) {
        this.companies = companies;
        this.store = store;
        this.clock = clock;
    }

    public Map<String, Object> overview(ApplicationPrincipal principal, UUID companyId, String period) {
        companies.requirePermission(principal, companyId, FinancePermissions.TITLES_READ);
        AuthorizedScope scope = companies.requireActiveMembership(principal, companyId);
        String normalized = period == null ? "month" : period.trim().toLowerCase(Locale.ROOT);
        if (!normalized.equals("month") && !normalized.equals("week") && !normalized.equals("year")) {
            throw new IllegalArgumentException("period");
        }
        ZonedDateTime now = clock.instant().atZone(ZONE);
        LocalDate today = now.toLocalDate();
        LocalDate fromDay = switch (normalized) {
            case "week" -> today.with(DayOfWeek.MONDAY);
            case "year" -> today.withDayOfYear(1);
            default -> today.withDayOfMonth(1);
        };
        Instant from = fromDay.atStartOfDay(ZONE).toInstant();
        Instant toExclusive = today.plusDays(1).atStartOfDay(ZONE).toInstant();
        OverviewFacts facts = store.load(scope, from, toExclusive, fromDay, today, today);
        return assemble(normalized, fromDay, today, now.toInstant(), facts);
    }

    static Map<String, Object> assemble(String period, LocalDate fromDay, LocalDate today, Instant now, OverviewFacts facts) {
        MoneyPart sales = sales(facts);
        MoneyPart fees = fees(facts);
        MoneyPart production = new MoneyPart("NAO_CONECTADO", null, List.of());
        MoneyPart expenses = expenses(facts);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("period", period);
        body.put("from", fromDay.toString());
        body.put("to", today.toString());
        body.put("title", title(period, today));
        body.put("rangeLabel", rangeLabel(fromDay, today));
        body.put("sales", part(sales));
        body.put("fees", part(fees));
        body.put("production", part(production));
        body.put("expenses", part(expenses));
        body.put("leftover", leftover(sales, fees, production, expenses));
        body.put("methods", methods(sales, facts));
        body.put("categories", categories(expenses, facts));
        body.put("cash", cash(facts, today));
        body.put("attention", attention(facts, today, now));
        body.put("statementLines", facts.statementLines());
        body.put("reconciliationPending", facts.reconciliationPending());
        body.put("lastPaySyncAt", facts.lastPaySync() == null ? null : facts.lastPaySync().toString());
        body.put("lastStatementAt", facts.lastStatement() == null ? null : facts.lastStatement().toString());
        body.put("accountName", facts.accountName());
        return body;
    }

    private static MoneyPart sales(OverviewFacts facts) {
        if (!facts.payAuthorized()) {
            return new MoneyPart("NAO_CONECTADO", null, List.of());
        }
        if (facts.sales().isEmpty()) {
            return new MoneyPart("NAO_APURADO", null, List.of());
        }
        long total = facts.sales().stream().mapToLong(MethodAmount::minor).sum();
        return new MoneyPart("APURADO", total, List.of());
    }

    private static MoneyPart fees(OverviewFacts facts) {
        if (facts.fees().lineCount() == 0 || facts.fees().measuredCount() == 0) {
            return new MoneyPart("NAO_APURADO", null, List.of());
        }
        return new MoneyPart("APURADO", facts.fees().feeMinor(), List.of());
    }

    private static MoneyPart expenses(OverviewFacts facts) {
        if (facts.expenses().isEmpty()) {
            return new MoneyPart("NAO_APURADO", null, List.of());
        }
        long total = facts.expenses().stream().mapToLong(CategoryAmount::minor).sum();
        return new MoneyPart("APURADO", total, List.of());
    }

    private static Map<String, Object> leftover(MoneyPart sales, MoneyPart fees, MoneyPart production, MoneyPart expenses) {
        List<String> missing = new ArrayList<>();
        if (!"APURADO".equals(sales.state())) {
            missing.add("Vendas");
        }
        if (!"APURADO".equals(fees.state())) {
            missing.add("Taxas");
        }
        if (!"APURADO".equals(production.state())) {
            missing.add("Custos de produção");
        }
        if (!"APURADO".equals(expenses.state())) {
            missing.add("Despesas");
        }
        long value = 0;
        boolean any = false;
        if (sales.minor() != null) {
            value += sales.minor();
            any = true;
        }
        if (fees.minor() != null) {
            value -= fees.minor();
            any = true;
        }
        if (expenses.minor() != null) {
            value -= expenses.minor();
            any = true;
        }
        Long partial = any ? value : null;
        boolean complete = missing.isEmpty();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("complete", complete);
        body.put("state", complete ? "APURADO" : "PARCIAL");
        body.put("minor", complete ? partial : partial);
        body.put("missing", missing);
        return body;
    }

    private static List<Map<String, Object>> methods(MoneyPart sales, OverviewFacts facts) {
        if (!"APURADO".equals(sales.state()) || sales.minor() == null || sales.minor() == 0) {
            return List.of();
        }
        Map<String, Long> grouped = new LinkedHashMap<>();
        grouped.put("Pix", 0L);
        grouped.put("Cartão de crédito", 0L);
        grouped.put("Cartão de débito", 0L);
        grouped.put("Outros", 0L);
        for (MethodAmount row : facts.sales()) {
            String key = methodLabel(row.method());
            grouped.put(key, grouped.get(key) + row.minor());
        }
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Map.Entry<String, Long> entry : grouped.entrySet()) {
            if (entry.getValue() == 0) {
                continue;
            }
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("label", entry.getKey());
            item.put("minor", entry.getValue());
            rows.add(item);
        }
        return rows;
    }

    static String methodLabel(String raw) {
        String value = raw == null ? "" : raw.toLowerCase(Locale.ROOT);
        if (value.contains("pix")) {
            return "Pix";
        }
        if (value.contains("debit") || value.contains("débito") || value.contains("debito")) {
            return "Cartão de débito";
        }
        if (value.contains("credit") || value.contains("crédito") || value.contains("credito")) {
            return "Cartão de crédito";
        }
        return "Outros";
    }

    private static List<Map<String, Object>> categories(MoneyPart expenses, OverviewFacts facts) {
        if (!"APURADO".equals(expenses.state())) {
            return List.of();
        }
        List<Map<String, Object>> rows = new ArrayList<>();
        for (CategoryAmount row : facts.expenses()) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("label", row.name());
            item.put("minor", row.minor());
            rows.add(item);
        }
        return rows;
    }

    private static Map<String, Object> cash(OverviewFacts facts, LocalDate today) {
        CashReading reading = facts.cash();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("state", reading.state());
        body.put("positionMinor", "APURADO".equals(reading.state()) ? reading.minor() : null);
        body.put("accountName", facts.accountName());
        if (!"APURADO".equals(reading.state()) || reading.minor() == null) {
            body.put("weeks", List.of());
            body.put("lowest", null);
            return body;
        }
        LocalDate start = today.with(DayOfWeek.MONDAY);
        long[] nets = new long[8];
        for (OpenTitle title : facts.openTitles()) {
            if (title.remainingMinor() <= 0 || title.due() == null) {
                continue;
            }
            int index = 0;
            if (!title.due().isBefore(start)) {
                long days = ChronoUnit.DAYS.between(start, title.due());
                if (days >= 56) {
                    continue;
                }
                index = (int) (days / 7);
            }
            long signed = "PAYABLE".equals(title.direction()) ? -title.remainingMinor() : title.remainingMinor();
            nets[index] += signed;
        }
        List<Map<String, Object>> weeks = new ArrayList<>();
        long running = reading.minor();
        int lowest = 0;
        long lowestValue = Long.MAX_VALUE;
        for (int i = 0; i < 8; i++) {
            running += nets[i];
            if (running < lowestValue) {
                lowestValue = running;
                lowest = i;
            }
            LocalDate weekStart = start.plusWeeks(i);
            Map<String, Object> week = new LinkedHashMap<>();
            week.put("start", weekStart.toString());
            week.put("label", weekStart.format(DAY));
            week.put("minor", running);
            weeks.add(week);
        }
        for (int i = 0; i < weeks.size(); i++) {
            weeks.get(i).put("lowest", i == lowest);
        }
        body.put("weeks", weeks);
        body.put("lowest", weeks.get(lowest));
        return body;
    }

    private static List<Map<String, Object>> attention(OverviewFacts facts, LocalDate today, Instant now) {
        List<Map<String, Object>> items = new ArrayList<>();
        facts.openTitles().stream()
                .filter(title -> "PAYABLE".equals(title.direction()))
                .filter(title -> title.due() != null && !title.due().isBefore(today) && !title.due().isAfter(today.plusDays(2)))
                .filter(title -> title.remainingMinor() > 0)
                .min(Comparator.comparing(OpenTitle::due))
                .ifPresent(title -> items.add(alert(
                        dueTag(today, title.due()),
                        title.description() + ": " + brl(title.remainingMinor()) + " vence em " + title.due().format(DAY) + "." + balanceNote(facts, title.remainingMinor()),
                        "/payables",
                        "Ver pagamento")));
        facts.openTitles().stream()
                .filter(title -> title.due() != null && title.due().isBefore(today) && title.remainingMinor() > 0)
                .min(Comparator.comparing(OpenTitle::due))
                .ifPresent(title -> {
                    boolean payable = "PAYABLE".equals(title.direction());
                    items.add(alert(
                            "Vencido",
                            title.description() + " de " + brl(title.remainingMinor()) + " venceu em " + title.due().format(DAY) + ".",
                            payable ? "/payables" : "/receivables",
                            payable ? "Ver pagamento" : "Ver recebimento"));
                });
        if (facts.reviewOccurrences() > 0) {
            items.add(alert(
                    "Extrato",
                    facts.reviewOccurrences() + " ocorrência(s) do extrato em revisão.",
                    "/financial-accounts/statement",
                    "Ver o extrato"));
        }
        if (facts.reconciliationPending() > 0) {
            items.add(alert(
                    "A conferir",
                    facts.reconciliationPending() + " lançamento(s) ainda sem conciliação.",
                    "/financial-accounts/reconciliation",
                    "Revisar " + facts.reconciliationPending() + " lançamentos"));
        }
        if (facts.payAuthorized()) {
            boolean stale = facts.lastPaySync() == null
                    || facts.lastPaySync().isBefore(now.minus(2, ChronoUnit.HOURS));
            if (stale) {
                items.add(alert(
                        "Sincronização",
                        facts.lastPaySync() == null
                                ? "O Pay ainda não teve uma sincronização concluída."
                                : "A última sincronização do Pay foi há mais de 2 horas.",
                        "/pay-receipts",
                        "Ver a sincronização"));
            }
        }
        return items.size() > 5 ? items.subList(0, 5) : items;
    }

    private static String dueTag(LocalDate today, LocalDate due) {
        long days = ChronoUnit.DAYS.between(today, due);
        if (days <= 0) {
            return "Vence hoje";
        }
        if (days == 1) {
            return "Vence amanhã";
        }
        return "Vence em até 2 dias";
    }

    private static String balanceNote(OverviewFacts facts, long remaining) {
        if (!"APURADO".equals(facts.cash().state()) || facts.cash().minor() == null) {
            return "";
        }
        return facts.cash().minor() >= remaining ? " Há saldo na conta." : " O saldo apurado não cobre este pagamento.";
    }

    static String brl(long minor) {
        boolean negative = minor < 0;
        long abs = Math.abs(minor);
        String digits = Long.toString(abs);
        String padded = digits.length() < 3 ? "0".repeat(3 - digits.length()) + digits : digits;
        String whole = padded.substring(0, padded.length() - 2);
        String fraction = padded.substring(padded.length() - 2);
        String grouped = whole.replaceAll("\\B(?=(\\d{3})+(?!\\d))", ".");
        return (negative ? "− " : "") + "R$ " + grouped + "," + fraction;
    }

    private static Map<String, Object> alert(String tag, String text, String href, String action) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("tag", tag);
        item.put("text", text);
        item.put("href", href);
        item.put("action", action);
        return item;
    }

    private static Map<String, Object> part(MoneyPart part) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("state", part.state());
        body.put("minor", "APURADO".equals(part.state()) ? part.minor() : null);
        return body;
    }

    private static String title(String period, LocalDate today) {
        String month = today.getMonth().getDisplayName(java.time.format.TextStyle.FULL, Locale.forLanguageTag("pt-BR"));
        month = month.substring(0, 1).toUpperCase(Locale.ROOT) + month.substring(1);
        return switch (period) {
            case "week" -> "Esta semana";
            case "year" -> "Ano até hoje";
            default -> month + " até hoje";
        };
    }

    private static String rangeLabel(LocalDate from, LocalDate to) {
        DateTimeFormatter full = DateTimeFormatter.ofPattern("d 'de' MMMM", Locale.forLanguageTag("pt-BR"));
        if (from.getMonth() == to.getMonth() && from.getYear() == to.getYear()) {
            return from.getDayOfMonth() + " a " + to.format(full);
        }
        return from.format(full) + " a " + to.format(full);
    }

    private record MoneyPart(String state, Long minor, List<String> unused) {}
}
