package br.com.actionfinance.application.finance;

import java.util.LinkedHashMap;
import java.util.Map;

public final class FinanceExceptions {

    private FinanceExceptions() {}

    public static final class ValidationException extends RuntimeException {
        private final Map<String, String> fields;

        public ValidationException(String message, Map<String, String> fields) {
            super(message);
            this.fields = Map.copyOf(fields);
        }

        public static ValidationException of(String field, String message) {
            Map<String, String> fields = new LinkedHashMap<>();
            fields.put(field, message);
            return new ValidationException(message, fields);
        }

        public Map<String, String> fields() {
            return fields;
        }
    }

    public static final class VersionConflictException extends RuntimeException {
        private final Map<String, String> fields;

        public VersionConflictException() {
            this("Este título foi alterado por outra pessoa.", Map.of());
        }

        public VersionConflictException(String message) {
            this(message, Map.of());
        }

        public VersionConflictException(String message, Map<String, String> fields) {
            super(message);
            this.fields = Map.copyOf(fields);
        }

        public Map<String, String> fields() {
            return fields;
        }
    }

    public static final class AlreadyReversedException extends RuntimeException {
        public AlreadyReversedException() {
            super("Esta baixa já foi estornada.");
        }
    }

    public static final class IdempotencyConflictException extends RuntimeException {
        public IdempotencyConflictException() {
            super("Esta chave de idempotência já foi usada com outro conteúdo.");
        }
    }

    public static final class CatalogConflictException extends RuntimeException {
        public CatalogConflictException(String message) {
            super(message);
        }
    }

    public static final class BindingConflictException extends RuntimeException {
        public BindingConflictException() {
            super("Esta referência já está vinculada a outro título desta empresa.");
        }
    }
}
