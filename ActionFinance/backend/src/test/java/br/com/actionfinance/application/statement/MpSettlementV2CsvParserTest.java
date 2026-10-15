package br.com.actionfinance.application.statement;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assumptions;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.LocalDate;
import java.util.HexFormat;

import static org.assertj.core.api.Assertions.assertThat;

class MpSettlementV2CsvParserTest {

    @Test
    void readsTheSanitizedSettlementAndLeavesTheAmbiguousPairOut() throws Exception {
        MpAccountMoneyCsvParser.ParseResult result = StatementCsvProfiles.parse(resource("settlement-v2-sanitizado.csv"));

        assertThat(result.recognized()).isTrue();
        assertThat(result.profileId()).isEqualTo("mp-settlement-v2-csv-1");
        assertThat(result.parserVersion()).isEqualTo("1");
        assertThat(result.currencyAssumed()).isFalse();
        assertThat(result.fileAccountRef()).isEqualTo("usr-sanitizado-031");
        assertThat(result.periodFrom()).isEqualTo(LocalDate.parse("2026-10-02"));
        assertThat(result.periodTo()).isEqualTo(LocalDate.parse("2026-10-08"));
        assertThat(result.rows()).hasSize(4);
        assertThat(result.rows().stream().filter(MpAccountMoneyCsvParser.ParsedRow::eligible)).hasSize(2);

        MpAccountMoneyCsvParser.ParsedRow fee = row(result, "pay-san-02");
        assertThat(fee.eligible()).isTrue();
        assertThat(fee.direction()).isEqualTo("IN");
        assertThat(fee.eventKind()).isEqualTo("SETTLEMENT");
        assertThat(fee.grossMinor()).isEqualTo(8000L);
        assertThat(fee.feeMinor()).isEqualTo(400L);
        assertThat(fee.netMinor()).isEqualTo(7600L);
        assertThat(fee.balanceEffect()).isEqualTo("AFFECTS");
        assertThat(fee.effectiveOn()).isEqualTo(LocalDate.parse("2026-10-08"));
        assertThat(fee.eventKey()).isEqualTo("MERCADOPAGO|mp-settlement-v2-csv-1|pay-san-02|SETTLEMENT");
        assertThat(fee.eventKey()).doesNotContain("|1|");
        assertThat(result.rows().stream().filter(item -> "pay-san-par-1".equals(item.sourceId())).noneMatch(MpAccountMoneyCsvParser.ParsedRow::eligible)).isTrue();
        assertThat(result.issues().stream().filter(issue -> "IDENTITY_INSUFFICIENT".equals(issue.code()))).hasSize(2);
        assertThat(result.issues().stream().filter(issue -> "EFFECT_UNVERIFIED".equals(issue.code()))).hasSize(2);
    }

    @Test
    void doesNotInferDirectionFromTheSettlementName() throws Exception {
        String csv = resourceText("settlement-v2-sanitizado.csv")
                .replace("pay-san-01", "pay-san-saida")
                .replace("100.00", "-5.00");
        MpAccountMoneyCsvParser.ParseResult result = MpSettlementV2CsvParser.parse(csv.getBytes(StandardCharsets.UTF_8));
        MpAccountMoneyCsvParser.ParsedRow outflow = row(result, "pay-san-saida");
        assertThat(outflow.eligible()).isTrue();
        assertThat(outflow.direction()).isEqualTo("OUT");
        assertThat(outflow.netMinor()).isEqualTo(500L);
    }

    @Test
    void preservesDivergentRealAmountAndFeeComponents() throws Exception {
        String base = resourceText("settlement-v2-sanitizado.csv");
        MpAccountMoneyCsvParser.ParseResult real = MpSettlementV2CsvParser.parse(base.replace("80.00;-4.00;76.00", "80.00;-4.00;90.00").getBytes(StandardCharsets.UTF_8));
        MpAccountMoneyCsvParser.ParsedRow divergent = row(real, "pay-san-02");
        assertThat(divergent.eligible()).isFalse();
        assertThat(divergent.grossMinor()).isEqualTo(8000L);
        assertThat(divergent.netMinor()).isEqualTo(7600L);
        assertThat(real.issues().stream().map(MpAccountMoneyCsvParser.RowIssue::message).anyMatch(message -> message.contains("nenhum substituiu o outro"))).isTrue();

        MpAccountMoneyCsvParser.ParseResult components = MpSettlementV2CsvParser.parse(base.replace("0.00;-4.00;0.00;0.00;0.00;1", "0.00;-1.00;0.00;0.00;0.00;1").getBytes(StandardCharsets.UTF_8));
        assertThat(row(components, "pay-san-02").eligible()).isFalse();
        assertThat(components.issues().stream().map(MpAccountMoneyCsvParser.RowIssue::message).anyMatch(message -> message.contains("não foi somada de novo"))).isTrue();
    }

    @Test
    void doesNotAssumeCurrencyOrTheLaboratorySeparator() throws Exception {
        String csv = resourceText("settlement-v2-sanitizado.csv").replace(";BRL;76.00;BRL;", ";BRL;76.00;USD;");
        MpAccountMoneyCsvParser.ParseResult mismatch = MpSettlementV2CsvParser.parse(csv.getBytes(StandardCharsets.UTF_8));
        assertThat(mismatch.currencyAssumed()).isFalse();
        assertThat(row(mismatch, "pay-san-02").eligible()).isFalse();
        assertThat(mismatch.issues().toString()).contains("divergem");

        String comma = resourceText("settlement-v2-sanitizado.csv").replace(';', ',');
        MpAccountMoneyCsvParser.ParseResult aliased = StatementCsvProfiles.parse(comma.getBytes(StandardCharsets.UTF_8));
        assertThat(aliased.recognized()).isFalse();
        assertThat(aliased.profileId()).isEmpty();
        assertThat(aliased.currencyAssumed()).isFalse();

        MpAccountMoneyCsvParser.ParseResult laboratory = StatementCsvProfiles.parse(
                "DATE,SOURCE_ID,RECORD_TYPE,NET_CREDIT_AMOUNT,CURRENCY\n2026-10-01,pay-sint-1,SETTLEMENT,10.00,BRL\n"
                        .getBytes(StandardCharsets.UTF_8));
        assertThat(laboratory.profileId()).isEqualTo(MpAccountMoneyCsvParser.PROFILE);
        assertThat(laboratory.profileId()).isNotEqualTo(MpSettlementV2CsvParser.PROFILE);
    }

    @Test
    void readsThePrivateReportStructureWithoutPublishingItsRows() throws Exception {
        Path report = privateReport();
        Assumptions.assumeTrue(report != null, "amostra privada ausente");
        byte[] bytes = Files.readAllBytes(report);
        assertThat(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))).isEqualTo("5cdfdeac66d9cb79d10d4daac92e8bff283bd2b600fb6794ab3e306a0b8622af");

        MpAccountMoneyCsvParser.ParseResult result = MpSettlementV2CsvParser.parse(bytes);
        assertThat(result.recognized()).isTrue();
        assertThat(result.profileId()).isEqualTo(MpSettlementV2CsvParser.PROFILE);
        assertThat(result.currencyAssumed()).isFalse();
        assertThat(result.fileAccountRef()).isNotBlank();
        assertThat(result.periodFrom()).isEqualTo(LocalDate.parse("2026-10-01"));
        assertThat(result.periodTo()).isEqualTo(LocalDate.parse("2026-10-14"));
        assertThat(result.rows()).hasSize(22);
        assertThat(result.rows().stream().filter(MpAccountMoneyCsvParser.ParsedRow::eligible)).hasSize(4);
        assertThat(result.rows().stream().map(MpAccountMoneyCsvParser.ParsedRow::eventKey).distinct().count()).isEqualTo(13);
        assertThat(result.rows().stream().filter(MpAccountMoneyCsvParser.ParsedRow::eligible))
                .allMatch(row -> "IN".equals(row.direction()) && "AFFECTS".equals(row.balanceEffect()) && !row.currencyAssumed());
        assertThat(result.issues().stream().filter(issue -> "IDENTITY_INSUFFICIENT".equals(issue.code()))).hasSize(18);
        assertThat(result.issues().stream().filter(issue -> "EFFECT_UNVERIFIED".equals(issue.code()))).hasSize(18);
        assertThat(result.rows().stream().filter(MpAccountMoneyCsvParser.ParsedRow::eligible).map(MpAccountMoneyCsvParser.ParsedRow::eventKey).filter(key -> key.contains("|1|")).count()).isZero();
    }

    private static Path privateReport() throws Exception {
        Path dir = Path.of("..", "documents", "data", "reports");
        if (!Files.isDirectory(dir)) {
            return null;
        }
        try (var listed = Files.list(dir)) {
            var found = listed.filter(path -> path.getFileName().toString().endsWith(".csv")).toList();
            return found.size() == 1 ? found.get(0) : null;
        }
    }

    private static MpAccountMoneyCsvParser.ParsedRow row(MpAccountMoneyCsvParser.ParseResult result, String sourceId) {
        return result.rows().stream().filter(row -> sourceId.equals(row.sourceId())).findFirst().orElseThrow();
    }

    private static byte[] resource(String name) throws Exception {
        return resourceText(name).getBytes(StandardCharsets.UTF_8);
    }

    private static String resourceText(String name) throws Exception {
        Path path = Path.of("src", "test", "resources", "statement", name);
        return Files.readString(path);
    }
}
