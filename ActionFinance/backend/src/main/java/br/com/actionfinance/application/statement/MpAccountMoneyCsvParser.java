package br.com.actionfinance.application.statement;

import java.nio.charset.CharacterCodingException;
import java.nio.charset.CharsetDecoder;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Perfil de laboratório {@code mp-account-money-csv-1}.
 * Não é o relatório de liquidação real, que tem outro parser.
 * CSV UTF-8, separador vírgula, decimal com ponto, data {@code yyyy-MM-dd}
 * ou instante ISO convertido para o dia civil em America/Sao_Paulo.
 * Não aceita ponto e vírgula, milhar com ponto nem vírgula decimal.
 *
 * <p>A chave do evento é origem + perfil + SOURCE_ID + RECORD_TYPE.
 * A versão do parser fica no lote e não entra na chave.
 * SOURCE_ID + RECORD_TYPE ainda não foi conferido num arquivo real desta conta:
 * conteúdo diferente com a mesma chave fica em revisão, sem fusão e sem ser tratado
 * como conflito comprovado de um único evento.
 * Sem a coluna CURRENCY a prévia existe, mas a linha não é confirmável e BRL não é presumido.
 * RELEASE, HOLD, UNBLOCK e INFO ficam em revisão até o efeito ser lido no relatório real.
 * Colunas de tarifa na mesma linha não são somadas de novo ao líquido, e diferença
 * entre bruto, tarifa e líquido é preservada.
 */
public final class MpAccountMoneyCsvParser {

    public static final String PROFILE = "mp-account-money-csv-1";
    public static final String PARSER_VERSION = "1";
    public static final ZoneId ZONE = ZoneId.of("America/Sao_Paulo");

    private static final List<String> REQUIRED = List.of("DATE", "SOURCE_ID", "RECORD_TYPE");
    private static final Set<String> KNOWN = Set.of(
            "DATE",
            "SOURCE_ID",
            "RECORD_TYPE",
            "EXTERNAL_REFERENCE",
            "DESCRIPTION",
            "NET_CREDIT_AMOUNT",
            "NET_DEBIT_AMOUNT",
            "GROSS_AMOUNT",
            "MP_FEE_AMOUNT",
            "FINANCING_FEE_AMOUNT",
            "SHIPPING_FEE_AMOUNT",
            "TAXES_AMOUNT",
            "CURRENCY",
            "ACCOUNT_EXTERNAL_REF");
    private static final Set<String> AFFECTS = Set.of(
            "SETTLEMENT", "FEE", "REFUND", "CHARGEBACK", "WITHDRAWAL", "TRANSFER", "PAYOUT");
    private static final Set<String> AVAILABILITY = Set.of("RELEASE", "HOLD", "UNBLOCK", "INFO");
    private static final List<String> FEE_COLUMNS = List.of(
            "MP_FEE_AMOUNT", "FINANCING_FEE_AMOUNT", "SHIPPING_FEE_AMOUNT", "TAXES_AMOUNT");

    private MpAccountMoneyCsvParser() {}

    public static ParseResult parse(byte[] bytes) {
        String text;
        try {
            text = decode(bytes);
        } catch (CharacterCodingException exception) {
            return ParseResult.rejected("O arquivo não está em UTF-8. Este perfil não tenta outra codificação.");
        }
        if (text.startsWith("\uFEFF")) {
            text = text.substring(1);
        }
        if (text.isBlank()) {
            return ParseResult.rejected("O arquivo está vazio.");
        }
        List<String> lines = splitLines(text);
        if (lines.isEmpty()) {
            return ParseResult.rejected("O arquivo está vazio.");
        }
        List<String> header = splitCsv(lines.get(0));
        String headerDiagnostic = diagnoseHeader(header);
        if (headerDiagnostic != null) {
            return ParseResult.rejected(headerDiagnostic);
        }
        Map<String, Integer> index = new LinkedHashMap<>();
        for (int i = 0; i < header.size(); i++) {
            index.put(header.get(i), i);
        }
        boolean accountColumn = index.containsKey("ACCOUNT_EXTERNAL_REF");
        boolean currencyColumn = index.containsKey("CURRENCY");
        List<ParsedRow> rows = new ArrayList<>();
        List<RowIssue> issues = new ArrayList<>();
        String fileAccount = null;
        for (int i = 1; i < lines.size(); i++) {
            String raw = lines.get(i);
            if (raw.isBlank()) {
                continue;
            }
            int lineNumber = i + 1;
            List<String> cells = splitCsv(raw);
            if (cells.size() != header.size()) {
                issues.add(new RowIssue(lineNumber, "INVALID", null, null, "A linha não tem o mesmo número de colunas do cabeçalho."));
                continue;
            }
            ParsedAttempt attempt = readRow(index, cells, lineNumber, raw, currencyColumn);
            if (attempt.issue() != null) {
                issues.add(attempt.issue());
                continue;
            }
            ParsedRow row = attempt.row();
            if ("UNVERIFIED".equals(row.balanceEffect())) {
                issues.add(new RowIssue(
                        lineNumber,
                        "EFFECT_UNVERIFIED",
                        row.sourceId(),
                        row.recordType(),
                        "O efeito deste tipo ainda não foi lido num relatório real desta conta. A linha fica em revisão, fora da soma de fluxo, e não foi classificada como mudança de disponível."));
            }
            if (accountColumn) {
                String ref = cell(index, cells, "ACCOUNT_EXTERNAL_REF");
                if (ref.isBlank()) {
                    issues.add(new RowIssue(lineNumber, "INVALID", row.sourceId(), row.recordType(), "A coluna de conta está vazia nesta linha."));
                    continue;
                }
                if (fileAccount == null) {
                    fileAccount = ref;
                } else if (!fileAccount.equals(ref)) {
                    issues.add(new RowIssue(lineNumber, "INVALID", row.sourceId(), row.recordType(), "O arquivo traz mais de uma conta. A confirmação fica bloqueada."));
                    fileAccount = "";
                }
            }
            rows.add(row);
        }
        if ("".equals(fileAccount)) {
            return new ParseResult(true, "O arquivo identifica contas diferentes. Nenhuma linha pode ser confirmada.", List.of(), issues, null, null, null, true, !currencyColumn, PROFILE, PARSER_VERSION);
        }
        markDuplicatesAndConflicts(rows, issues);
        LocalDate from = null;
        LocalDate to = null;
        for (ParsedRow row : rows) {
            if (row.effectiveOn() == null) {
                continue;
            }
            from = from == null || row.effectiveOn().isBefore(from) ? row.effectiveOn() : from;
            to = to == null || row.effectiveOn().isAfter(to) ? row.effectiveOn() : to;
        }
        String diagnostic = null;
        if (!currencyColumn) {
            for (ParsedRow row : rows) {
                row.eligible = false;
            }
            diagnostic = "O arquivo não informa a moeda. A prévia permanece disponível, mas a confirmação e a soma financeira ficam bloqueadas. Nenhuma moeda foi presumida.";
        }
        return new ParseResult(true, diagnostic, List.copyOf(rows), List.copyOf(issues), from, to, fileAccount, accountColumn, !currencyColumn, PROFILE, PARSER_VERSION);
    }

    public static String eventKey(String sourceId, String recordType) {
        return "MERCADOPAGO|" + PROFILE + "|" + sourceId + "|" + recordType;
    }

    private static ParsedAttempt readRow(
            Map<String, Integer> index, List<String> cells, int lineNumber, String raw, boolean currencyColumn) {
        String sourceId = cell(index, cells, "SOURCE_ID");
        String recordType = cell(index, cells, "RECORD_TYPE").toUpperCase(Locale.ROOT);
        if (sourceId.isBlank() || recordType.isBlank()) {
            return ParsedAttempt.issue(new RowIssue(
                    lineNumber,
                    "INVALID",
                    sourceId.isBlank() ? null : sourceId,
                    recordType.isBlank() ? null : recordType,
                    "Sem SOURCE_ID e RECORD_TYPE não há identidade de evento. A linha permanece não importável."));
        }
        if (sourceId.length() > 80 || recordType.length() > 24) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", null, null, "SOURCE_ID ou RECORD_TYPE excede o tamanho aceito por este perfil."));
        }
        if (!recordType.matches("[A-Z][A-Z0-9_]{0,23}")) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, "Tipo de evento fora do formato deste perfil."));
        }
        String currency = currencyColumn ? cell(index, cells, "CURRENCY").toUpperCase(Locale.ROOT) : "BRL";
        if (currency.isBlank()) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, "Moeda vazia. Este perfil não assume BRL quando a coluna existe e está em branco."));
        }
        if (!"BRL".equals(currency)) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "UNSUPPORTED_CURRENCY", sourceId, recordType, "Moeda " + currency + " sem regra de conversão. Nenhuma conversão foi feita."));
        }
        Money credit = money(index, cells, "NET_CREDIT_AMOUNT");
        Money debit = money(index, cells, "NET_DEBIT_AMOUNT");
        Money gross = money(index, cells, "GROSS_AMOUNT");
        if (credit.error() != null || debit.error() != null || gross.error() != null) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, firstError(credit, debit, gross)));
        }
        Money fee = fee(index, cells);
        if (fee.error() != null) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, fee.error()));
        }
        if (credit.present() && debit.present() && credit.minor() > 0 && debit.minor() > 0) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, "Crédito e débito positivos na mesma linha. O perfil não escolhe um dos dois."));
        }
        String dateText = cell(index, cells, "DATE");
        LocalDate effective;
        try {
            effective = dateText.isBlank() ? null : civilDate(dateText);
        } catch (DateTimeParseException exception) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, "Data fora de yyyy-MM-dd ou de um instante ISO."));
        }
        String direction;
        Long net;
        boolean netAbsent;
        if (credit.present() && credit.minor() > 0 && (!debit.present() || debit.minor() == 0)) {
            direction = "IN";
            net = credit.minor();
            netAbsent = false;
        } else if (debit.present() && debit.minor() > 0 && (!credit.present() || credit.minor() == 0)) {
            direction = "OUT";
            net = debit.minor();
            netAbsent = false;
        } else if (credit.present() || debit.present()) {
            direction = "NONE";
            net = 0L;
            netAbsent = false;
        } else {
            direction = "NONE";
            net = null;
            netAbsent = true;
        }
        boolean effectUnverified = AVAILABILITY.contains(recordType);
        String effect = effectUnverified ? "UNVERIFIED" : AFFECTS.contains(recordType) ? "AFFECTS" : "UNKNOWN";
        String external = blankToNull(cell(index, cells, "EXTERNAL_REFERENCE"));
        if (external != null && external.length() > 80) {
            return ParsedAttempt.issue(new RowIssue(lineNumber, "INVALID", sourceId, recordType, "EXTERNAL_REFERENCE acima de 80 caracteres."));
        }
        String description = blankToNull(cell(index, cells, "DESCRIPTION"));
        if (description != null && description.length() > 300) {
            description = description.substring(0, 300);
        }
        String hash = sha256(String.join("|",
                sourceId,
                recordType,
                external == null ? "" : external,
                effective == null ? "" : effective.toString(),
                direction,
                gross.present() ? Long.toString(gross.minor()) : "",
                fee.present() ? Long.toString(fee.minor()) : "",
                netAbsent ? "" : Long.toString(net),
                currencyColumn ? currency : "",
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
                effective,
                direction,
                recordType,
                effect,
                gross.present() ? gross.minor() : null,
                !gross.present(),
                fee.present() ? fee.minor() : null,
                !fee.present(),
                net,
                netAbsent,
                !currencyColumn,
                "UNKNOWN",
                !effectUnverified);
        return ParsedAttempt.row(row);
    }

    private static void markDuplicatesAndConflicts(List<ParsedRow> rows, List<RowIssue> issues) {
        Map<String, ParsedRow> first = new LinkedHashMap<>();
        for (ParsedRow row : rows) {
            ParsedRow previous = first.get(row.eventKey());
            if (previous == null) {
                first.put(row.eventKey(), row);
                continue;
            }
            if (previous.contentHash().equals(row.contentHash())) {
                row.eligible = false;
                issues.add(new RowIssue(row.lineNumber(), "DUPLICATE", row.sourceId(), row.recordType(), "Mesmo evento e mesmo conteúdo já aparecem neste arquivo."));
            } else {
                previous.eligible = false;
                row.eligible = false;
                issues.add(new RowIssue(previous.lineNumber(), "IDENTITY_INSUFFICIENT", previous.sourceId(), previous.recordType(), "SOURCE_ID e RECORD_TYPE iguais com conteúdo diferente. Essa chave não distingue ocorrências legítimas de uma reapresentação. As linhas ficam em revisão, sem fusão e sem gravação."));
                issues.add(new RowIssue(row.lineNumber(), "IDENTITY_INSUFFICIENT", row.sourceId(), row.recordType(), "SOURCE_ID e RECORD_TYPE iguais com conteúdo diferente. Essa chave não distingue ocorrências legítimas de uma reapresentação. As linhas ficam em revisão, sem fusão e sem gravação."));
            }
        }
    }

    private static String diagnoseHeader(List<String> header) {
        if (header.size() == 1 && header.get(0).contains(";")) {
            return "Separador incompatível. O perfil mp-account-money-csv-1 usa vírgula, não ponto e vírgula.";
        }
        List<String> unknown = new ArrayList<>();
        List<String> seen = new ArrayList<>();
        for (String name : header) {
            if (!KNOWN.contains(name)) {
                unknown.add(name.isBlank() ? "(vazia)" : name);
            }
            if (seen.contains(name)) {
                return "Cabeçalho com coluna repetida: " + name + ".";
            }
            seen.add(name);
        }
        if (!unknown.isEmpty()) {
            return "Coluna não reconhecida neste perfil: " + String.join(", ", unknown) + ". O arquivo não foi interpretado por aproximação.";
        }
        for (String required : REQUIRED) {
            if (!seen.contains(required)) {
                return "Falta a coluna obrigatória " + required + ".";
            }
        }
        return null;
    }

    private static Money fee(Map<String, Integer> index, List<String> cells) {
        boolean any = false;
        long sum = 0;
        for (String column : FEE_COLUMNS) {
            if (!index.containsKey(column)) {
                continue;
            }
            Money part = money(index, cells, column);
            if (part.error() != null) {
                return part;
            }
            if (part.present()) {
                any = true;
                sum += part.minor();
            }
        }
        return any ? Money.of(sum) : Money.absent();
    }

    private static Money money(Map<String, Integer> index, List<String> cells, String column) {
        if (!index.containsKey(column)) {
            return Money.absent();
        }
        String text = cell(index, cells, column);
        if (text.isBlank()) {
            return Money.absent();
        }
        if (text.startsWith("-")) {
            return Money.error("Valor negativo em " + column + ". Este perfil usa crédito e débito separados, sem sinal.");
        }
        if (text.contains(",")) {
            return Money.error("Valor com vírgula em " + column + ". Este perfil usa ponto decimal.");
        }
        if (!text.matches("\\d+(\\.\\d{1,2})?")) {
            return Money.error("Valor inválido em " + column + ".");
        }
        String[] parts = text.split("\\.");
        long major = Long.parseLong(parts[0]);
        int fraction = parts.length == 1 ? 0 : Integer.parseInt(parts[1].length() == 1 ? parts[1] + "0" : parts[1]);
        try {
            return Money.of(Math.addExact(Math.multiplyExact(major, 100), fraction));
        } catch (ArithmeticException exception) {
            return Money.error("Valor grande demais em " + column + ".");
        }
    }

    private static LocalDate civilDate(String text) {
        if (text.contains("T")) {
            return OffsetDateTime.parse(text).atZoneSameInstant(ZONE).toLocalDate();
        }
        return LocalDate.parse(text);
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
        return "Valor inválido.";
    }

    static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(exception);
        }
    }

    private static String decode(byte[] bytes) throws CharacterCodingException {
        CharsetDecoder decoder = StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT);
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

    static List<String> splitCsv(String line) {
        List<String> cells = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char ch = line.charAt(i);
            if (quoted) {
                if (ch == '"') {
                    if (i + 1 < line.length() && line.charAt(i + 1) == '"') {
                        current.append('"');
                        i++;
                    } else {
                        quoted = false;
                    }
                } else {
                    current.append(ch);
                }
            } else if (ch == '"') {
                quoted = true;
            } else if (ch == ',') {
                cells.add(current.toString());
                current.setLength(0);
            } else {
                current.append(ch);
            }
        }
        cells.add(current.toString());
        return cells;
    }

    private static String trimRaw(String raw) {
        return raw.length() <= 2000 ? raw : raw.substring(0, 2000);
    }

    private record Money(boolean present, long minor, String error) {
        static Money absent() {
            return new Money(false, 0, null);
        }

        static Money of(long minor) {
            return new Money(true, minor, null);
        }

        static Money error(String error) {
            return new Money(false, 0, error);
        }
    }

    private record ParsedAttempt(ParsedRow row, RowIssue issue) {
        static ParsedAttempt row(ParsedRow row) {
            return new ParsedAttempt(row, null);
        }

        static ParsedAttempt issue(RowIssue issue) {
            return new ParsedAttempt(null, issue);
        }
    }

    public record ParseResult(
            boolean recognized,
            String fileDiagnostic,
            List<ParsedRow> rows,
            List<RowIssue> issues,
            LocalDate periodFrom,
            LocalDate periodTo,
            String fileAccountRef,
            boolean accountColumnPresent,
            boolean currencyAssumed,
            String profileId,
            String parserVersion) {
        static ParseResult rejected(String diagnostic) {
            return new ParseResult(false, diagnostic, List.of(), List.of(), null, null, null, false, false, PROFILE, PARSER_VERSION);
        }
    }

    public static final class ParsedRow {
        private final int lineNumber;
        private final String rawText;
        private final boolean truncated;
        private final String eventKey;
        private final String contentHash;
        private final String sourceId;
        private final String recordType;
        private final String externalReference;
        private final String description;
        private final LocalDate effectiveOn;
        private final String direction;
        private final String eventKind;
        private final String balanceEffect;
        private final Long grossMinor;
        private final boolean grossAbsent;
        private final Long feeMinor;
        private final boolean feeAbsent;
        private final Long netMinor;
        private final boolean netAbsent;
        private final boolean currencyAssumed;
        private final String availability;
        private boolean eligible;

        ParsedRow(
                int lineNumber,
                String rawText,
                boolean truncated,
                String eventKey,
                String contentHash,
                String sourceId,
                String recordType,
                String externalReference,
                String description,
                LocalDate effectiveOn,
                String direction,
                String eventKind,
                String balanceEffect,
                Long grossMinor,
                boolean grossAbsent,
                Long feeMinor,
                boolean feeAbsent,
                Long netMinor,
                boolean netAbsent,
                boolean currencyAssumed,
                String availability,
                boolean eligible) {
            this.lineNumber = lineNumber;
            this.rawText = rawText;
            this.truncated = truncated;
            this.eventKey = eventKey;
            this.contentHash = contentHash;
            this.sourceId = sourceId;
            this.recordType = recordType;
            this.externalReference = externalReference;
            this.description = description;
            this.effectiveOn = effectiveOn;
            this.direction = direction;
            this.eventKind = eventKind;
            this.balanceEffect = balanceEffect;
            this.grossMinor = grossMinor;
            this.grossAbsent = grossAbsent;
            this.feeMinor = feeMinor;
            this.feeAbsent = feeAbsent;
            this.netMinor = netMinor;
            this.netAbsent = netAbsent;
            this.currencyAssumed = currencyAssumed;
            this.availability = availability;
            this.eligible = eligible;
        }

        public int lineNumber() { return lineNumber; }
        public String rawText() { return rawText; }
        public boolean truncated() { return truncated; }
        public String eventKey() { return eventKey; }
        public String contentHash() { return contentHash; }
        public String sourceId() { return sourceId; }
        public String recordType() { return recordType; }
        public String externalReference() { return externalReference; }
        public String description() { return description; }
        public LocalDate effectiveOn() { return effectiveOn; }
        public String direction() { return direction; }
        public String eventKind() { return eventKind; }
        public String balanceEffect() { return balanceEffect; }
        public Long grossMinor() { return grossMinor; }
        public boolean grossAbsent() { return grossAbsent; }
        public Long feeMinor() { return feeMinor; }
        public boolean feeAbsent() { return feeAbsent; }
        public Long netMinor() { return netMinor; }
        public boolean netAbsent() { return netAbsent; }
        public boolean currencyAssumed() { return currencyAssumed; }
        public String availability() { return availability; }
        public boolean eligible() { return eligible; }

        void markIneligible() {
            this.eligible = false;
        }
    }

    public record RowIssue(int lineNumber, String code, String sourceId, String recordType, String message) {}
}
