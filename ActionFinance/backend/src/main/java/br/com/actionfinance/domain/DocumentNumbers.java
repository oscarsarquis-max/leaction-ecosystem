package br.com.actionfinance.domain;

import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;

/**
 * Formato e dígitos verificadores oficiais. Não prova existência, situação fiscal nem titularidade.
 *
 * <p>CNPJ (RFB, manual de cálculo do DV): 12 caracteres alfanuméricos + 2 DVs numéricos.
 * Valor do caractere = ASCII − 48. Pesos 5,4,3,2,9,8,7,6,5,4,3,2 (1º DV) e
 * 6,5,4,3,2,9,8,7,6,5,4,3,2 (2º DV). Fonte:
 * https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj
 *
 * <p>CPF: 11 dígitos com DV módulo 11. OTHER: só apresentação prevista, sem colapsar lixo em identidade.
 */
public final class DocumentNumbers {

    private static final int[] CNPJ_WEIGHTS_DV1 = {5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2};
    private static final int[] CNPJ_WEIGHTS_DV2 = {6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2};

    private DocumentNumbers() {}

    public record NormalizedDocument(String country, DocumentType type, String display, String normalized) {}

    public static String normalizeToken(String raw) {
        if (raw == null) {
            return null;
        }
        if (!raw.matches("[A-Za-z0-9.\\-/\\s]*")) {
            return null;
        }
        String compact = raw.replaceAll("[.\\-/\\s]", "").toUpperCase();
        return compact.isEmpty() ? null : compact;
    }

    public static NormalizedDocument parse(String country, String typeRaw, String number) {
        return parse(country, typeRaw, number, PersonKind.UNSPECIFIED);
    }

    public static NormalizedDocument parse(String country, String typeRaw, String number, PersonKind personKind) {
        String trimmedNumber = number == null ? "" : number.trim();
        String trimmedType = typeRaw == null ? "" : typeRaw.trim();
        String trimmedCountry = country == null ? "" : country.trim().toUpperCase();
        PersonKind kind = personKind == null ? PersonKind.UNSPECIFIED : personKind;
        if (trimmedNumber.isEmpty() && trimmedType.isEmpty() && trimmedCountry.isEmpty()) {
            return null;
        }
        if (trimmedNumber.isEmpty() || trimmedType.isEmpty() || !trimmedCountry.matches("[A-Z]{2}")) {
            throw ValidationException.of(
                    "documentNumber",
                    "Informe país (duas letras), tipo e número juntos, ou deixe os três vazios.");
        }
        DocumentType type;
        try {
            type = DocumentType.valueOf(trimmedType);
        } catch (IllegalArgumentException ex) {
            throw ValidationException.of("documentType", "Tipo de documento não reconhecido.");
        }
        if (!trimmedNumber.matches("[A-Za-z0-9.\\-/\\s]+")) {
            throw ValidationException.of(
                    "documentNumber",
                    "O documento contém caracteres que não são de apresentação. Corrija ou remova.");
        }
        String normalized = normalizeToken(trimmedNumber);
        if (normalized == null) {
            throw ValidationException.of("documentNumber", "Documento informado é inválido.");
        }
        switch (type) {
            case CPF -> validateCpf(normalized, trimmedCountry, kind);
            case CNPJ -> validateCnpj(normalized, trimmedCountry, kind);
            case OTHER -> validateOther(normalized, trimmedCountry);
        }
        return new NormalizedDocument(trimmedCountry, type, trimmedNumber, normalized);
    }

    private static void validateCpf(String normalized, String country, PersonKind kind) {
        if (!"BR".equals(country)) {
            throw ValidationException.of("documentCountry", "CPF só é aceito com país BR.");
        }
        if (kind == PersonKind.LEGAL) {
            throw ValidationException.of("personKind", "Pessoa jurídica não usa CPF. Corrija o tipo ou o documento.");
        }
        if (!normalized.matches("\\d{11}")) {
            throw ValidationException.of("documentNumber", "CPF deve ter 11 dígitos, com pontuação opcional.");
        }
        if (allSame(normalized) || !cpfDigitsValid(normalized)) {
            throw ValidationException.of("documentNumber", "CPF com dígitos verificadores inválidos.");
        }
    }

    private static void validateCnpj(String normalized, String country, PersonKind kind) {
        if (!"BR".equals(country)) {
            throw ValidationException.of("documentCountry", "CNPJ só é aceito com país BR.");
        }
        if (kind == PersonKind.NATURAL) {
            throw ValidationException.of("personKind", "Pessoa física não usa CNPJ. Corrija o tipo ou o documento.");
        }
        if (!normalized.matches("[A-Z0-9]{12}\\d{2}")) {
            throw ValidationException.of(
                    "documentNumber",
                    "CNPJ deve ter 12 caracteres alfanuméricos e dois dígitos verificadores numéricos.");
        }
        if ("00000000000000".equals(normalized) || !cnpjDigitsValid(normalized)) {
            throw ValidationException.of("documentNumber", "CNPJ com dígitos verificadores inválidos.");
        }
    }

    private static void validateOther(String normalized, String country) {
        if (normalized.length() > 32 || !normalized.matches("[A-Z0-9]{1,32}")) {
            throw ValidationException.of("documentNumber", "Documento de outro tipo deve ter 1 a 32 letras ou números.");
        }
        if ("BR".equals(country) && (normalized.matches("\\d{11}") || normalized.matches("[A-Z0-9]{12}\\d{2}"))) {
            throw ValidationException.of(
                    "documentType",
                    "Este número no Brasil deve usar o tipo CPF ou CNPJ, não Outro.");
        }
    }

    static boolean cpfDigitsValid(String digits) {
        int d1 = mod11(digits.substring(0, 9), 10);
        int d2 = mod11(digits.substring(0, 9) + d1, 11);
        return digits.charAt(9) - '0' == d1 && digits.charAt(10) - '0' == d2;
    }

    static boolean cnpjDigitsValid(String value) {
        int d1 = cnpjDv(value.substring(0, 12), CNPJ_WEIGHTS_DV1);
        int d2 = cnpjDv(value.substring(0, 12) + d1, CNPJ_WEIGHTS_DV2);
        return value.charAt(12) - '0' == d1 && value.charAt(13) - '0' == d2;
    }

    private static int cnpjDv(String body, int[] weights) {
        int sum = 0;
        for (int i = 0; i < weights.length; i++) {
            sum += (body.charAt(i) - 48) * weights[i];
        }
        int rem = sum % 11;
        return rem < 2 ? 0 : 11 - rem;
    }

    private static int mod11(String body, int startWeight) {
        int sum = 0;
        for (int i = 0; i < body.length(); i++) {
            sum += (body.charAt(i) - '0') * (startWeight - i);
        }
        int rem = sum % 11;
        return rem < 2 ? 0 : 11 - rem;
    }

    private static boolean allSame(String value) {
        return value.chars().allMatch(ch -> ch == value.charAt(0));
    }

    public static String mask(String normalized, boolean reveal) {
        if (normalized == null || normalized.isBlank()) {
            return null;
        }
        if (reveal) {
            return normalized;
        }
        if (normalized.length() <= 4) {
            return "••••";
        }
        return "••••" + normalized.substring(normalized.length() - 2);
    }
}
