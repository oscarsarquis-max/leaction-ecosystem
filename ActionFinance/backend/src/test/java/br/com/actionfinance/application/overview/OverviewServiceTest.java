package br.com.actionfinance.application.overview;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class OverviewServiceTest {

    private static final LocalDate TODAY = LocalDate.of(2026, 11, 10);
    private static final Instant NOW = Instant.parse("2026-11-10T18:00:00Z");

    @Test
    void eachBlockUsesOnlyMeasuredNumbers() {
        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW, new OverviewFacts(
                true,
                List.of(
                        new OverviewFacts.MethodAmount("pix", 311_000),
                        new OverviewFacts.MethodAmount("credit_card", 259_000),
                        new OverviewFacts.MethodAmount("debit_card", 78_000)),
                new OverviewFacts.FeeReading(20, 20, 27_860),
                List.of(
                        new OverviewFacts.CategoryAmount("Aluguel", 70_000),
                        new OverviewFacts.CategoryAmount("Energia", 49_000)),
                new OverviewFacts.CashReading("APURADO", 421_530L),
                List.of(),
                0,
                0,
                12,
                NOW,
                NOW,
                "Mercado Pago"));

        assertEquals("APURADO", part(body, "sales").get("state"));
        assertEquals(648_000L, part(body, "sales").get("minor"));
        assertEquals("APURADO", part(body, "fees").get("state"));
        assertEquals(27_860L, part(body, "fees").get("minor"));
        assertEquals("NAO_CONECTADO", part(body, "production").get("state"));
        assertNull(part(body, "production").get("minor"));
        assertEquals("APURADO", part(body, "expenses").get("state"));
        assertEquals(119_000L, part(body, "expenses").get("minor"));
        assertEquals(List.of("Pix", "Cartão de crédito", "Cartão de débito"), labels(body, "methods"));
        assertEquals(List.of("Aluguel", "Energia"), labels(body, "categories"));
        assertEquals(12, body.get("statementLines"));
    }

    @Test
    void absenceIsNotZero() {
        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW, new OverviewFacts(
                false,
                List.of(),
                new OverviewFacts.FeeReading(0, 0, 0),
                List.of(),
                new OverviewFacts.CashReading("NAO_CONECTADO", null),
                List.of(),
                0,
                0,
                0,
                null,
                null,
                null));

        assertEquals("NAO_CONECTADO", part(body, "sales").get("state"));
        assertNull(part(body, "sales").get("minor"));
        assertEquals("NAO_APURADO", part(body, "fees").get("state"));
        assertNull(part(body, "fees").get("minor"));
        assertEquals("NAO_APURADO", part(body, "expenses").get("state"));
        assertNull(part(body, "expenses").get("minor"));
        assertEquals("NAO_CONECTADO", cash(body).get("state"));
        assertNull(cash(body).get("positionMinor"));
        assertEquals(List.of(), cash(body).get("weeks"));
        assertNull(leftover(body).get("minor"));
    }

    @Test
    void authorizedSalesWithoutRowsStayUnmeasured() {
        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW, base().withSales(true, List.of()).toFacts());
        assertEquals("NAO_APURADO", part(body, "sales").get("state"));
        assertNull(part(body, "sales").get("minor"));
        assertEquals(List.of(), body.get("methods"));
    }

    @Test
    void statementWithoutMeasuredFeesStaysUnmeasured() {
        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW,
                base().withFees(new OverviewFacts.FeeReading(8, 0, 0)).toFacts());
        assertEquals("NAO_APURADO", part(body, "fees").get("state"));
        assertNull(part(body, "fees").get("minor"));
    }

    @Test
    void leftoverIsPartialUntilEveryPartIsMeasured() {
        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW, new OverviewFacts(
                true,
                List.of(new OverviewFacts.MethodAmount("pix", 648_000)),
                new OverviewFacts.FeeReading(4, 4, 27_860),
                List.of(new OverviewFacts.CategoryAmount("Aluguel", 119_000)),
                new OverviewFacts.CashReading("NAO_CONECTADO", null),
                List.of(),
                0,
                0,
                0,
                null,
                null,
                null));

        assertEquals(false, leftover(body).get("complete"));
        assertEquals("PARCIAL", leftover(body).get("state"));
        assertEquals(501_140L, leftover(body).get("minor"));
        assertEquals(List.of("Custos de produção"), leftover(body).get("missing"));
    }

    @Test
    void eightWeeksMarkTheLowestAndKeepOverdueInTheFirstWeek() {
        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW, new OverviewFacts(
                true,
                List.of(new OverviewFacts.MethodAmount("pix", 100)),
                new OverviewFacts.FeeReading(1, 1, 1),
                List.of(new OverviewFacts.CategoryAmount("Aluguel", 1)),
                new OverviewFacts.CashReading("APURADO", 421_530L),
                List.of(
                        new OverviewFacts.OpenTitle("PAYABLE", "Farinha vencida", LocalDate.of(2026, 11, 1), 100_000),
                        new OverviewFacts.OpenTitle("PAYABLE", "Aluguel", LocalDate.of(2026, 11, 24), 500_000)),
                0,
                0,
                0,
                null,
                null,
                "Mercado Pago"));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> weeks = (List<Map<String, Object>>) cash(body).get("weeks");
        assertEquals(8, weeks.size());
        assertEquals("2026-11-09", weeks.get(0).get("start"));
        assertEquals(321_530L, weeks.get(0).get("minor"));
        assertEquals(Boolean.FALSE, weeks.get(0).get("lowest"));
        assertEquals(-178_470L, weeks.get(2).get("minor"));
        assertEquals(Boolean.TRUE, weeks.get(2).get("lowest"));
        assertEquals("2026-11-23", ((Map<?, ?>) cash(body).get("lowest")).get("start"));
    }

    @Test
    void attentionKeepsTheUrgentOrderAndStopsAtFive() {
        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW, new OverviewFacts(
                true,
                List.of(new OverviewFacts.MethodAmount("pix", 100)),
                new OverviewFacts.FeeReading(1, 1, 1),
                List.of(new OverviewFacts.CategoryAmount("Aluguel", 1)),
                new OverviewFacts.CashReading("APURADO", 900_000L),
                List.of(
                        new OverviewFacts.OpenTitle("PAYABLE", "Farinha", LocalDate.of(2026, 11, 11), 86_000),
                        new OverviewFacts.OpenTitle("PAYABLE", "Gás", LocalDate.of(2026, 11, 12), 10_000),
                        new OverviewFacts.OpenTitle("RECEIVABLE", "Cliente", LocalDate.of(2026, 11, 2), 4_000)),
                2,
                3,
                10,
                NOW.minusSeconds(3 * 3600),
                NOW,
                "Mercado Pago"));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) body.get("attention");
        assertEquals(5, items.size());
        assertEquals(List.of("Vence amanhã", "Vencido", "Extrato", "A conferir", "Sincronização"),
                items.stream().map(item -> item.get("tag")).toList());
        assertEquals("/payables", items.get(0).get("href"));
        assertTrue(String.valueOf(items.get(0).get("text")).contains("R$ 860,00"));
        assertTrue(String.valueOf(items.get(0).get("text")).contains("Há saldo na conta."));
        assertEquals("/receivables", items.get(1).get("href"));
        assertEquals("/financial-accounts/reconciliation", items.get(2 + 1).get("href"));
    }

    @Test
    void lojaWithReceiptsAndNoOpeningBalanceStillAnswers() {
        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW, new OverviewFacts(
                true,
                List.of(new OverviewFacts.MethodAmount("pix", 150_000)),
                new OverviewFacts.FeeReading(0, 0, 0),
                List.of(),
                new OverviewFacts.CashReading("NAO_APURADO", null),
                List.of(),
                0,
                0,
                0,
                NOW,
                null,
                "Conta da loja"));

        assertEquals("APURADO", part(body, "sales").get("state"));
        assertEquals(150_000L, part(body, "sales").get("minor"));
        assertEquals("NAO_APURADO", part(body, "fees").get("state"));
        assertNull(part(body, "fees").get("minor"));
        assertEquals("NAO_APURADO", part(body, "expenses").get("state"));
        assertNull(part(body, "expenses").get("minor"));
        assertEquals("NAO_CONECTADO", part(body, "production").get("state"));
        assertEquals("NAO_APURADO", cash(body).get("state"));
        assertNull(cash(body).get("positionMinor"));
        assertEquals(List.of(), cash(body).get("weeks"));
        assertNull(body.get("lastStatementAt"));
        assertEquals(NOW.toString(), body.get("lastPaySyncAt"));
        assertEquals(List.of("Taxas", "Custos de produção", "Despesas"), leftover(body).get("missing"));
    }

    @Test
    void cardIsNamedCartaoAndUnknownStaysOutros() {
        assertEquals("Cartão", OverviewService.methodLabel("card"));
        assertEquals("Pix", OverviewService.methodLabel("pix"));
        assertEquals("Cartão de crédito", OverviewService.methodLabel("credit_card"));
        assertEquals("Cartão de débito", OverviewService.methodLabel("debit_card"));
        assertEquals("Saldo Mercado Pago", OverviewService.methodLabel("account_money"));
        assertEquals("Boleto", OverviewService.methodLabel("ticket"));
        assertEquals("Boleto", OverviewService.methodLabel("bolbradesco"));
        assertEquals("Outros", OverviewService.methodLabel("crypto"));

        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW, new OverviewFacts(
                true,
                List.of(new OverviewFacts.MethodAmount("card", 42_000)),
                new OverviewFacts.FeeReading(1, 1, 1),
                List.of(new OverviewFacts.CategoryAmount("Aluguel", 1)),
                new OverviewFacts.CashReading("NAO_CONECTADO", null),
                List.of(),
                0,
                0,
                0,
                NOW,
                null,
                null));
        assertEquals(List.of("Cartão"), labels(body, "methods"));
    }

    @Test
    void freshPaySyncDoesNotAskForAttention() {
        Map<String, Object> body = OverviewService.assemble("month", TODAY.withDayOfMonth(1), TODAY, NOW,
                base().withSync(NOW.minusSeconds(600)).toFacts());
        assertEquals(List.of(), body.get("attention"));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> part(Map<String, Object> body, String name) {
        return (Map<String, Object>) body.get(name);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> cash(Map<String, Object> body) {
        return (Map<String, Object>) body.get("cash");
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> leftover(Map<String, Object> body) {
        return (Map<String, Object>) body.get("leftover");
    }

    @SuppressWarnings("unchecked")
    private static List<String> labels(Map<String, Object> body, String name) {
        return ((List<Map<String, Object>>) body.get(name)).stream().map(row -> String.valueOf(row.get("label"))).toList();
    }

    private static Draft base() {
        return new Draft();
    }

    private static final class Draft {
        private boolean pay = true;
        private List<OverviewFacts.MethodAmount> sales = List.of(new OverviewFacts.MethodAmount("pix", 100));
        private OverviewFacts.FeeReading fees = new OverviewFacts.FeeReading(1, 1, 1);
        private List<OverviewFacts.CategoryAmount> expenses = List.of(new OverviewFacts.CategoryAmount("Aluguel", 1));
        private Instant sync = NOW;

        Draft withSales(boolean authorized, List<OverviewFacts.MethodAmount> rows) {
            pay = authorized;
            sales = rows;
            return this;
        }

        Draft withFees(OverviewFacts.FeeReading reading) {
            fees = reading;
            return this;
        }

        Draft withSync(Instant instant) {
            sync = instant;
            return this;
        }

        private OverviewFacts toFacts() {
            return new OverviewFacts(
                    pay,
                    sales,
                    fees,
                    expenses,
                    new OverviewFacts.CashReading("NAO_CONECTADO", null),
                    List.of(),
                    0,
                    0,
                    0,
                    sync,
                    null,
                    null);
        }
    }
}
