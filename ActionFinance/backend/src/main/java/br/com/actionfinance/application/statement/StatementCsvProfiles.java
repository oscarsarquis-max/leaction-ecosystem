package br.com.actionfinance.application.statement;

import br.com.actionfinance.application.statement.MpAccountMoneyCsvParser.ParseResult;

import java.nio.charset.CharacterCodingException;
import java.nio.charset.CharsetDecoder;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;

/** Encaminha o arquivo ao perfil reconhecido pelo cabeçalho. Não trata um perfil como o outro. */
public final class StatementCsvProfiles {

    private StatementCsvProfiles() {}

    public static ParseResult parse(byte[] bytes) {
        String first = firstLine(bytes);
        if (first == null) {
            return new ParseResult(false, "O arquivo não está em UTF-8. Nenhum perfil tenta outra codificação.", java.util.List.of(), java.util.List.of(), null, null, null, false, false, "", "");
        }
        if (first.contains("SETTLEMENT_NET_AMOUNT") && first.contains("TRANSACTION_DATE") && first.contains(";")) {
            return MpSettlementV2CsvParser.parse(bytes);
        }
        if (!first.contains("SETTLEMENT_NET_AMOUNT")) {
            return MpAccountMoneyCsvParser.parse(bytes);
        }
        return new ParseResult(
                false,
                "Nenhum perfil reconhecido. O relatório de liquidação usa ponto e vírgula e as colunas TRANSACTION_DATE e SETTLEMENT_NET_AMOUNT. O CSV de laboratório usa vírgula e as colunas DATE, SOURCE_ID e RECORD_TYPE. O arquivo não foi interpretado por aproximação.",
                java.util.List.of(),
                java.util.List.of(),
                null,
                null,
                null,
                false,
                false,
                "",
                "");
    }

    private static String firstLine(byte[] bytes) {
        if (bytes == null || bytes.length == 0) {
            return "";
        }
        try {
            CharsetDecoder decoder = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT);
            String text = decoder.decode(java.nio.ByteBuffer.wrap(bytes)).toString();
            if (text.startsWith("\uFEFF")) {
                text = text.substring(1);
            }
            int breakAt = text.indexOf('\n');
            int carriage = text.indexOf('\r');
            if (carriage >= 0 && (breakAt < 0 || carriage < breakAt)) {
                breakAt = carriage;
            }
            return breakAt < 0 ? text : text.substring(0, breakAt);
        } catch (CharacterCodingException exception) {
            return null;
        }
    }
}
