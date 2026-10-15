package br.com.actionfinance.application.statement;

import br.com.actionfinance.application.statement.MpAccountMoneyCsvParser.ParseResult;
import br.com.actionfinance.application.statement.MpAccountMoneyCsvParser.ParsedRow;
import br.com.actionfinance.application.statement.MpAccountMoneyCsvParser.RowIssue;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Relatório de liquidação exportado, perfil {@code mp-settlement-v2-csv-1}.
 * CSV UTF-8, separador ponto e vírgula, decimal com ponto e sinal, instante com deslocamento.
 * A data da linha é a de aprovação ({@code SETTLEMENT_DATE}).
 * A direção sai do sinal de {@code SETTLEMENT_NET_AMOUNT}, não do nome SETTLEMENT.
 * A versão do parser não entra na chave.
 */
public final class MpSettlementV2CsvParser {

    public static final String PROFILE = "mp-settlement-v2-csv-1";
    public static final String PARSER_VERSION = "1";

    private static final List<String> REQUIRED = List.of(
            "TRANSACTION_DATE",
            "SETTLEMENT_DATE",
            "SOURCE_ID",
            "TRANSACTION_TYPE",
            "TRANSACTION_AMOUNT",
            "FEE_AMOUNT",
            "REAL_AMOUNT",
            "TRANSACTION_CURRENCY",
            "SETTLEMENT_NET_AMOUNT",
            "SETTLEMENT_CURRENCY",
            "USER_ID",
            "IS_RELEASED");
    private static final List<String> FEE_COMPONENTS = List.of(
            "MKP_FEE_AMOUNT", "FINANCING_FEE_AMOUNT", "SHIPPING_FEE_AMOUNT", "TAXES_AMOUNT");
    private static final Set<String> KNOWN = Set.of(
            "TRANSACTION_DATE", "SETTLEMENT_DATE", "SOURCE_ID", "PAYMENT_METHOD_TYPE", "TRANSACTION_TYPE",
            "TRANSACTION_AMOUNT", "FEE_AMOUNT", "REAL_AMOUNT", "TAXES_AMOUNT", "BUSINESS_UNIT", "SUB_UNIT",
            "MONEY_RELEASE_DATE", "EXTERNAL_REFERENCE", "USER_ID", "PAYMENT_METHOD", "SITE",
            "TRANSACTION_CURRENCY", "SETTLEMENT_NET_AMOUNT", "SETTLEMENT_CURRENCY", "COUPON_AMOUNT",
            "MKP_FEE_AMOUNT", "FINANCING_FEE_AMOUNT", "SHIPPING_FEE_AMOUNT", "SELLER_AMOUNT", "INSTALLMENTS",
            "INSTALLMENT_NUMBER", "INSTALLMENT_NET_AMOUNT", "IS_RELEASED", "DESCRIPTION", "METADATA",
            "OPERATION_TAGS", "SALE_DETAIL", "PRODUCT_SKU", "TRANSACTION_INTENT_ID", "ORDER_MP", "ORDER_ID",
            "PURCHASE_ID", "APPLICATION_ID", "STORE_ID", "STORE_NAME", "EXTERNAL_STORE_ID", "TAX_DETAIL",
            "TAXES_DISAGGREGATED", "POI_WALLET_NAME", "POI_BANK_NAME", "INVOICING_PERIOD");

    private MpSettlementV2CsvParser() {}

    public static ParseResult parse(byte[] bytes) {
        String text;
        try {
            text = decode(bytes);
        } catch (java.nio.charset.CharacterCodingException exception) {
            return unrecognized("O arquivo não está em UTF-8. Este perfil não tenta outra codificação.");
        }
        if (text.startsWith("\uFEFF")) {
            text = text.substring(1);
        }
        List<String> lines = splitLines(text);
        if (lines.isEmpty()) {
            return unrecognized("O arquivo está vazio.");
        }
        List<String> header = split(lines.get(0));
        String headerDiagnostic = diagnoseHeader(header);
        if (headerDiagnostic != null) {
            return unrecognized(headerDiagnostic);
        }
        Map<String, Integer> index = new LinkedHashMap<>();
        for (int i = 0; i < header.size(); i++) {
            index.put(header.get(i), i);
        }
        List<ParsedRow> rows = new ArrayList<>();
        List<RowIssue> issues = new ArrayList<>();
        String fileAccount = null;
        boolean mixedAccounts = false;
        for (int i = 1; i < lines.size(); i++) {
            String raw = lines.get(i);
            if (raw.isBlank()) {
                continue;
            }
            int lineNumber = i + 1;
            List<String> cells = split(raw);
            if (cells.size() != header.size()) {
                issues.add(new RowIssue(lineNumber, "INVALID", null, null, "A linha não tem o mesmo número de colunas do cabeçalho."));
                continue;
            }
            ParsedAttempt attempt = readRow(index, cells, lineNumber, raw);
            issues.addAll(attempt.issues());
            if (attempt.row() == null) {
                continue;
            }
            ParsedRow row = attempt.row();
            String user = cell(index, cells, "USER_ID");
            if (user.isBlank()) {
                row.markIneligible();
                issues.add(new RowIssue(lineNumber, "INVALID", row.sourceId(), row.recordType(), "USER_ID vazio. A linha não identifica a conta."));
            } else if (fileAccount == null) {
                fileAccount = user;
            } else if (!fileAccount.equals(user)) {
                mixedAccounts = true;
                row.markIneligible();
                issues.add(new RowIssue(lineNumber, "INVALID", row.sourceId(), row.recordType(), "O arquivo traz mais de uma conta. A confirmação fica bloqueada."));
            }
            rows.add(row);
        }
        if (mixedAccounts) {
            for (ParsedRow row : rows) {
                row.markIneligible();
            }
            return new ParseResult(true, "O arquivo identifica contas diferentes. Nenhuma linha pode ser confirmada.", List.copyOf(rows), List.copyOf(issues), null, null, "", true, false, PROFILE, PARSER_VERSION);
        }
        markIdentity(rows, issues);
        LocalDate from = null;
        LocalDate to = null;
        for (ParsedRow row : rows) {
            if (row.effectiveOn() == null) {
                continue;
            }
            from = from == null || row.effectiveOn().isBefore(from) ? row.effectiveOn() : from;
            to = to == null || row.effectiveOn().isAfter(to) ? row.effectiveOn() : to;
        }
        return new ParseResult(true, null, List.copyOf(rows), List.copyOf(issues), from, to, fileAccount, true, false, PROFILE, PARSER_VERSION);
    }

    private static ParsedAttempt readRow(Map<String, Integer> index, List<String> cells, int lineNumber, String raw) {
        String sourceId = cell(index, cells, "SOURCE_ID");
        String recordType = cell(index, cells, "TRANSACTION_TYPE").toUpperCase(Locale.ROOT);
        if (sourceId.isBlank() || recordType.isBlank()) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", blankToNull(sourceId), blankToNull(recordType), "Sem SOURCE_ID e TRANSACTION_TYPE não há identidade. A linha permanece na prévia e não é importável."));
        }
        if (sourceId.length() > 80 || recordType.length() > 24 || !recordType.matches("[A-Z][A-Z0-9_]{0,23}")) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", null, null, "SOURCE_ID ou TRANSACTION_TYPE fora do formato aceito por este perfil."));
        }
        String transactionCurrency = cell(index, cells, "TRANSACTION_CURRENCY").toUpperCase(Locale.ROOT);
        String settlementCurrency = cell(index, cells, "SETTLEMENT_CURRENCY").toUpperCase(Locale.ROOT);
        RowIssue currencyIssue = currencyIssue(lineNumber, sourceId, recordType, transactionCurrency, settlementCurrency);
        Money gross = money(index, cells, "TRANSACTION_AMOUNT");
        Money fee = money(index, cells, "FEE_AMOUNT");
        Money real = money(index, cells, "REAL_AMOUNT");
        Money net = money(index, cells, "SETTLEMENT_NET_AMOUNT");
        String amountError = firstError(gross, fee, real, net);
        if (amountError != null) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, amountError));
        }
        LocalDate approval;
        try {
            approval = requiredDate(cell(index, cells, "SETTLEMENT_DATE"));
        } catch (DateTimeParseException | IllegalArgumentException exception) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, "SETTLEMENT_DATE ausente ou fora de um instante com deslocamento. TRANSACTION_DATE não foi usada no lugar."));
        }
        try {
            requiredDate(cell(index, cells, "TRANSACTION_DATE"));
        } catch (DateTimeParseException | IllegalArgumentException exception) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, "TRANSACTION_DATE fora de um instante com deslocamento. Ela não foi trocada pela data de aprovação."));
        }
        String releaseText = cell(index, cells, "MONEY_RELEASE_DATE");
        if (!releaseText.isBlank()) {
            try {
                requiredDate(releaseText);
            } catch (DateTimeParseException | IllegalArgumentException exception) {
                return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, "MONEY_RELEASE_DATE fora de um instante com deslocamento. Ela não foi copiada para a data da linha."));
            }
        }
        boolean eligible = currencyIssue == null;
        List<RowIssue> extra = new ArrayList<>();
        if (currencyIssue != null) {
            extra.add(currencyIssue);
        }
        if (real.present() && net.present() && real.minor() != net.minor()) {
            eligible = false;
            extra.add(new RowIssue(lineNumber, "AMOUNT_DIVERGENCE", sourceId, recordType, "REAL_AMOUNT e SETTLEMENT_NET_AMOUNT divergem. Os dois foram preservados e nenhum substituiu o outro."));
        } else if (!real.present() || !net.present() || !gross.present()) {
            eligible = false;
            extra.add(new RowIssue(lineNumber, "AMOUNT_ABSENT", sourceId, recordType, "Bruto, líquido da operação ou líquido que impactou a conta está ausente. A ausência não foi preenchida com zero."));
        }
        if (!fee.present()) {
            eligible = false;
            extra.add(new RowIssue(lineNumber, "AMOUNT_ABSENT", sourceId, recordType, "FEE_AMOUNT ausente. A tarifa não foi tratada como zero nem somada ao líquido."));
        } else if (fee.present() && componentAbsent(index, cells)) {
            eligible = false;
            extra.add(new RowIssue(lineNumber, "AMOUNT_ABSENT", sourceId, recordType, "Um componente da tarifa está ausente. Ele não foi tratado como zero e a tarifa não foi somada de novo ao líquido."));
        } else if (fee.present() && componentsDiverge(index, cells, fee.minor())) {
            eligible = false;
            extra.add(new RowIssue(lineNumber, "AMOUNT_DIVERGENCE", sourceId, recordType, "FEE_AMOUNT não fecha com os componentes presentes. A diferença foi preservada e a tarifa não foi somada de novo ao líquido."));
        }
        if (gross.present() && fee.present() && net.present() && gross.minor() + fee.minor() != net.minor()) {
            eligible = false;
            extra.add(new RowIssue(lineNumber, "AMOUNT_DIVERGENCE", sourceId, recordType, "TRANSACTION_AMOUNT mais FEE_AMOUNT não fecha com SETTLEMENT_NET_AMOUNT. Os valores foram preservados, sem ajuste."));
        }
        Long storedFee = null;
        if (fee.present() && fee.minor() < 0) {
            storedFee = Math.negateExact(fee.minor());
        } else if (fee.present() && fee.minor() > 0) {
            eligible = false;
            storedFee = fee.minor();
            extra.add(new RowIssue(lineNumber, "AMOUNT_DIVERGENCE", sourceId, recordType, "FEE_AMOUNT positivo não foi convertido em custo. O sinal foi preservado e a linha fica fora da confirmação."));
        } else if (fee.present()) {
            storedFee = 0L;
        }
        String released = cell(index, cells, "IS_RELEASED").toLowerCase(Locale.ROOT);
        String effect = "AFFECTS";
        if (!"true".equals(released)) {
            eligible = false;
            effect = "UNVERIFIED";
            extra.add(new RowIssue(lineNumber, "EFFECT_UNVERIFIED", sourceId, recordType, "IS_RELEASED não confirma a liberação do dinheiro. O líquido e a liberação não foram tratados como a mesma coisa. A linha fica na prévia, fora da soma, e não foi classificada como mudança de disponível."));
        }
        String direction = "NONE";
        Long storedNet = null;
        boolean netAbsent = !net.present();
        if (net.present() && net.minor() > 0) {
            direction = "IN";
            storedNet = net.minor();
        } else if (net.present() && net.minor() < 0) {
            direction = "OUT";
            storedNet = Math.negateExact(net.minor());
        } else if (net.present()) {
            storedNet = 0L;
        }
        String external = blankToNull(cell(index, cells, "EXTERNAL_REFERENCE"));
        if (external != null && external.length() > 80) {
            eligible = false;
            extra.add(new RowIssue(lineNumber, "INVALID", sourceId, recordType, "EXTERNAL_REFERENCE acima de 80 caracteres."));
            external = null;
        }
        String description = blankToNull(cell(index, cells, "DESCRIPTION"));
        if (description != null && description.length() > 300) {
            description = description.substring(0, 300);
        }
        String hash = MpAccountMoneyCsvParser.sha256(String.join("|",
                sourceId,
                recordType,
                external == null ? "" : external,
                approval.toString(),
                direction,
                gross.present() ? Long.toString(gross.minor()) : "",
                fee.present() ? Long.toString(fee.minor()) : "",
                real.present() ? Long.toString(real.minor()) : "",
                net.present() ? Long.toString(net.minor()) : "",
                transactionCurrency,
                settlementCurrency,
                released,
                description == null ? "" : description));
        ParsedRow row = new ParsedRow(
                lineNumber,
                trimRaw(raw),
                raw.length() > 2000,
                eventKey(sourceId, recordType),
                hash,
                sourceId,
                recordType,
                external,
                description,
                approval,
                direction,
                recordType,
                effect,
                gross.present() ? gross.minor() : null,
                !gross.present(),
                storedFee,
                !fee.present(),
                storedNet,
                netAbsent,
                false,
                eligible);
        return ParsedAttempt.row(row, extra);
    }

    private static void markIdentity(List<ParsedRow> rows, List<RowIssue> issues) {
        Map<String, ParsedRow> first = new LinkedHashMap<>();
        for (ParsedRow row : rows) {
            ParsedRow previous = first.get(row.eventKey());
            if (previous == null) {
                first.put(row.eventKey(), row);
                continue;
            }
            if (previous.contentHash().equals(row.contentHash())) {
                row.markIneligible();
                issues.add(new RowIssue(row.lineNumber(), "DUPLICATE", row.sourceId(), row.recordType(), "Mesmo evento e mesmo conteúdo já aparecem neste arquivo. A segunda ocorrência não entra."));
            } else {
                previous.markIneligible();
                row.markIneligible();
                String message = "SOURCE_ID e TRANSACTION_TYPE iguais, sem coluna que separe as ocorrências. Os valores diferem e não foram fundidos. As linhas ficam na prévia e fora da confirmação.";
                issues.add(new RowIssue(previous.lineNumber(), "IDENTITY_INSUFFICIENT", previous.sourceId(), previous.recordType(), message));
                issues.add(new RowIssue(row.lineNumber(), "IDENTITY_INSUFFICIENT", row.sourceId(), row.recordType(), message));
            }
        }
    }

    private static RowIssue currencyIssue(int lineNumber, String sourceId, String recordType, String transactionCurrency, String settlementCurrency) {
        if (transactionCurrency.isBlank() || settlementCurrency.isBlank()) {
            return new RowIssue(lineNumber, "INVALID", sourceId, recordType, "Moeda em branco. BRL não foi presumido.");
        }
        if (!transactionCurrency.equals(settlementCurrency)) {
            return new RowIssue(lineNumber, "UNSUPPORTED_CURRENCY", sourceId, recordType, "As colunas de moeda divergem. Nenhuma foi escolhida e nenhuma conversão foi feita.");
        }
        if (!"BRL".equals(transactionCurrency)) {
            return new RowIssue(lineNumber, "UNSUPPORTED_CURRENCY", sourceId, recordType, "Moeda " + transactionCurrency + " sem regra de conversão. Nenhuma conversão foi feita.");
        }
        return null;
    }

    private static boolean componentAbsent(Map<String, Integer> index, List<String> cells) {
        for (String column : FEE_COMPONENTS) {
            if (!index.containsKey(column)) {
                continue;
            }
            Money part = money(index, cells, column);
            if (part.error() != null || !part.present()) {
                return true;
            }
        }
        return false;
    }

    private static boolean componentsDiverge(Map<String, Integer> index, List<String> cells, long feeMinor) {
        boolean any = false;
        long sum = 0;
        for (String column : FEE_COMPONENTS) {
            if (!index.containsKey(column)) {
                continue;
            }
            Money part = money(index, cells, column);
            if (!part.present()) {
                return false;
            }
            any = true;
            sum += part.minor();
        }
        return any && sum != feeMinor;
    }

    static String eventKey(String sourceId, String recordType) {
        return "MERCADOPAGO|" + PROFILE + "|" + sourceId + "|" + recordType;
    }

    private static ParseResult unrecognized(String diagnostic) {
        return new ParseResult(false, diagnostic, List.of(), List.of(), null, null, null, false, false, PROFILE, PARSER_VERSION);
    }

    private static LocalDate requiredDate(String text) {
        if (text == null || text.isBlank() || !text.contains("T")) {
            throw new IllegalArgumentException("date");
        }
        return OffsetDateTime.parse(text).atZoneSameInstant(MpAccountMoneyCsvParser.ZONE).toLocalDate();
    }

    private static Money money(Map<String, Integer> index, List<String> cells, String column) {
        if (!index.containsKey(column)) {
            return Money.absent();
        }
        String text = cell(index, cells, column);
        if (text.isBlank()) {
            return Money.absent();
        }
        boolean negative = text.startsWith("-");
        String digits = negative ? text.substring(1) : text;
        if (digits.startsWith("-") || text.contains(",")) {
            return Money.error("Valor inválido em " + column + ". Este perfil usa ponto decimal.");
        }
        if (!digits.matches("\\d+(\\.\\d{1,2})?")) {
            return Money.error("Valor inválido em " + column + ".");
        }
        String[] parts = digits.split("\\.");
        long major = Long.parseLong(parts[0]);
        int fraction = parts.length == 1 ? 0 : Integer.parseInt(parts[1].length() == 1 ? parts[1] + "0" : parts[1]);
        try {
            long minor = Math.addExact(Math.multiplyExact(major, 100), fraction);
            return Money.of(negative ? Math.negateExact(minor) : minor);
        } catch (ArithmeticException exception) {
            return Money.error("Valor grande demais em " + column + ".");
        }
    }

    private static String diagnoseHeader(List<String> header) {
        if (header.size() == 1 && header.get(0).contains(",")) {
            return "Separador incompatível. O perfil mp-settlement-v2-csv-1 usa ponto e vírgula, não vírgula.";
        }
        List<String> seen = new ArrayList<>();
        for (String name : header) {
            if (name.isBlank()) {
                return "Cabeçalho com coluna vazia.";
            }
            if (!KNOWN.contains(name)) {
                return "Coluna não reconhecida neste perfil: " + name + ". O arquivo não foi interpretado por aproximação.";
            }
            if (seen.contains(name)) {
                return "Cabeçalho com coluna repetida: " + name + ".";
            }
            seen.add(name);
        }
        for (String required : REQUIRED) {
            if (!seen.contains(required)) {
                return "Falta a coluna obrigatória " + required + ".";
            }
        }
        return null;
    }

    private static String decode(byte[] bytes) throws java.nio.charset.CharacterCodingException {
        java.nio.charset.CharsetDecoder decoder = java.nio.charset.StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
                .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT);
        return decoder.decode(java.nio.ByteBuffer.wrap(bytes)).toString();
    }

    private static List<String> splitLines(String text) {
        String normalized = text.replace("\r\n", "\n").replace('\r', '\n');
        List<String> lines = new ArrayList<>();
        for (String line : normalized.split("\n", -1)) {
            lines.add(line);
        }
        while (!lines.isEmpty() && lines.get(lines.size() - 1).isBlank()) {
            lines.remove(lines.size() - 1);
        }
        return lines;
    }

    static List<String> split(String line) {
        List<String> cells = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        int i = 0;
        while (i < line.length()) {
            if (line.charAt(i) == '"') {
                i++;
                while (i < line.length()) {
                    char ch = line.charAt(i);
                    if (ch == '"') {
                        if (i + 1 < line.length() && line.charAt(i + 1) == '"') {
                            current.append('"');
                            i += 2;
                        } else {
                            i++;
                            break;
                        }
                    } else {
                        current.append(ch);
                        i++;
                    }
                }
                if (i < line.length() && line.charAt(i) == ';') {
                    cells.add(current.toString());
                    current.setLength(0);
                    i++;
                }
            } else if (line.charAt(i) == ';') {
                cells.add(current.toString());
                current.setLength(0);
                i++;
            } else {
                current.append(line.charAt(i));
                i++;
            }
        }
        cells.add(current.toString());
        return cells;
    }

    private static String cell(Map<String, Integer> index, List<String> cells, String name) {
        Integer position = index.get(name);
        if (position == null || position >= cells.size()) {
            return "";
        }
        return cells.get(position).trim();
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    private static String firstError(Money... values) {
        for (Money value : values) {
            if (value.error() != null) {
                return value.error();
            }
        }
        return null;
    }

    private static String trimRaw(String raw) {
        return raw.length() <= 2000 ? raw : raw.substring(0, 2000);
    }

    private record Money(boolean present, long minor, String error) {
        static Money absent() { return new Money(false, 0, null); }
        static Money of(long minor) { return new Money(true, minor, null); }
        static Money error(String error) { return new Money(false, 0, error); }
    }

    private record ParsedAttempt(ParsedRow row, List<RowIssue> issues) {
        static ParsedAttempt row(ParsedRow row, List<RowIssue> issues) { return new ParsedAttempt(row, issues); }
        static ParsedAttempt issue(RowIssue issue) { return new ParsedAttempt(null, List.of(issue)); }
    }
}
