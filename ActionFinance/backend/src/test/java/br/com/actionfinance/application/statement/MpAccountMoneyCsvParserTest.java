package br.com.actionfinance.application.statement;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

class MpAccountMoneyCsvParserTest {

    @Test
    void readsTheConcreteProfileAndKeepsDistinctEvents() {
        MpAccountMoneyCsvParser.ParseResult result = MpAccountMoneyCsvParser.parse(csv("""
                DATE,SOURCE_ID,RECORD_TYPE,NET_CREDIT_AMOUNT,NET_DEBIT_AMOUNT,GROSS_AMOUNT,MP_FEE_AMOUNT,DESCRIPTION,CURRENCY
                2026-10-01,pay-sint-100,SETTLEMENT,85.00,,90.00,5.00,Venda,BRL
                2026-10-01,pay-sint-100,RELEASE,90.00,,,,Liberacao,BRL
                2026-10-01,pay-sint-100,SETTLEMENT,85.00,,90.00,5.00,Venda,BRL
                2026-10-01,pay-sint-200,SETTLEMENT,85.00,,90.00,5.00,Outra venda,BRL
                2026-10-02,pay-sint-100,SETTLEMENT,10.00,,10.00,0.00,Conflito,BRL
                2026-10-02,pay-sint-zero,SETTLEMENT,0.00,,,,Zero explicito,BRL
                2026-10-02,pay-sint-vazio,SETTLEMENT,,,,,Ausente,BRL
                2026-10-02,,FEE,1.00,,,,Sem identidade,BRL
                2026-10-02,pay-sint-usd,SETTLEMENT,1.00,,,,Outra moeda,USD
                """).getBytes(StandardCharsets.UTF_8));

        assertThat(result.recognized()).isTrue();
        assertThat(result.currencyAssumed()).isFalse();
        assertThat(result.rows()).extracting(MpAccountMoneyCsvParser.ParsedRow::eventKey)
                .contains(
                        "MERCADOPAGO|mp-account-money-csv-1|pay-sint-100|SETTLEMENT",
                        "MERCADOPAGO|mp-account-money-csv-1|pay-sint-100|RELEASE",
                        "MERCADOPAGO|mp-account-money-csv-1|pay-sint-200|SETTLEMENT");
        assertThat(result.rows()).filteredOn(row -> row.sourceId().equals("pay-sint-100") && row.recordType().equals("SETTLEMENT") && row.lineNumber() == 2)
                .singleElement()
                .satisfies(row -> {
                    assertThat(row.eligible()).isFalse();
                    assertThat(row.netMinor()).isEqualTo(8500L);
                    assertThat(row.feeMinor()).isEqualTo(500L);
                    assertThat(row.balanceEffect()).isEqualTo("AFFECTS");
                });
        assertThat(result.rows()).filteredOn(row -> row.recordType().equals("RELEASE"))
                .singleElement()
                .satisfies(row -> {
                    assertThat(row.eligible()).isFalse();
                    assertThat(row.balanceEffect()).isEqualTo("UNVERIFIED");
                });
        assertThat(MpAccountMoneyCsvParser.eventKey("pay-sint-100", "SETTLEMENT"))
                .isEqualTo("MERCADOPAGO|mp-account-money-csv-1|pay-sint-100|SETTLEMENT")
                .doesNotContain("|" + MpAccountMoneyCsvParser.PARSER_VERSION + "|");
        assertThat(result.rows()).filteredOn(row -> "pay-sint-zero".equals(row.sourceId()))
                .singleElement()
                .satisfies(row -> {
                    assertThat(row.netAbsent()).isFalse();
                    assertThat(row.netMinor()).isZero();
                });
        assertThat(result.rows()).filteredOn(row -> "pay-sint-vazio".equals(row.sourceId()))
                .singleElement()
                .satisfies(row -> assertThat(row.netAbsent()).isTrue());
        assertThat(result.issues()).extracting(MpAccountMoneyCsvParser.RowIssue::code)
                .contains("DUPLICATE", "IDENTITY_INSUFFICIENT", "INVALID", "UNSUPPORTED_CURRENCY", "EFFECT_UNVERIFIED");
        assertThat(result.issues()).extracting(MpAccountMoneyCsvParser.RowIssue::message)
                .anyMatch(message -> message.contains("sem regra de conversão"));
    }

    @Test
    void keepsPreviewWithoutCurrencyAndDoesNotConfirmAPresumedBrl() {
        MpAccountMoneyCsvParser.ParseResult result = MpAccountMoneyCsvParser.parse("""
                DATE,SOURCE_ID,RECORD_TYPE,NET_CREDIT_AMOUNT
                2026-10-01,pay-sint-sem-moeda,SETTLEMENT,10.00
                """.getBytes(StandardCharsets.UTF_8));

        assertThat(result.recognized()).isTrue();
        assertThat(result.currencyAssumed()).isTrue();
        assertThat(result.fileDiagnostic()).contains("Nenhuma moeda foi presumida");
        assertThat(result.rows()).allMatch(row -> !row.eligible());
    }

    @Test
    void doesNotMergeTwoRefundsThatShareOnlySourceAndType() {
        MpAccountMoneyCsvParser.ParseResult result = MpAccountMoneyCsvParser.parse("""
                DATE,SOURCE_ID,RECORD_TYPE,NET_DEBIT_AMOUNT,CURRENCY
                2026-10-11,pay-sint-estorno,REFUND,10.00,BRL
                2026-10-11,pay-sint-estorno,REFUND,4.00,BRL
                """.getBytes(StandardCharsets.UTF_8));

        assertThat(result.rows()).hasSize(2).allMatch(row -> !row.eligible());
        assertThat(result.rows()).extracting(MpAccountMoneyCsvParser.ParsedRow::netMinor).containsExactly(1000L, 400L);
        assertThat(result.issues()).extracting(MpAccountMoneyCsvParser.RowIssue::code).containsOnly("IDENTITY_INSUFFICIENT");
    }

    @Test
    void rejectsADifferentSeparatorWithoutGuessing() {
        MpAccountMoneyCsvParser.ParseResult result = MpAccountMoneyCsvParser.parse(
                "DATE;SOURCE_ID;RECORD_TYPE\n2026-10-01;pay-sint-1;SETTLEMENT\n".getBytes(StandardCharsets.UTF_8));

        assertThat(result.recognized()).isFalse();
        assertThat(result.rows()).isEmpty();
        assertThat(result.fileDiagnostic()).contains("vírgula");
    }

    private static String csv(String text) {
        return text.stripIndent();
    }
}
