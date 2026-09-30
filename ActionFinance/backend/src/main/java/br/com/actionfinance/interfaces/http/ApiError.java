package br.com.actionfinance.interfaces.http;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.Map;

@JsonInclude(JsonInclude.Include.NON_EMPTY)
public record ApiError(String code, String message, String correlationId, Map<String, String> fields) {
    public ApiError(String code, String message, String correlationId) {
        this(code, message, correlationId, Map.of());
    }
}
