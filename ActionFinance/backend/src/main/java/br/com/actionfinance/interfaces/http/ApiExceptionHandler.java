package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.finance.FinanceExceptions.AlreadyReversedException;
import br.com.actionfinance.application.finance.FinanceExceptions.IdempotencyConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.NoHandlerFoundException;

import java.util.Map;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(SecurityException.class)
    ResponseEntity<ApiError> forbidden(SecurityException exception, HttpServletRequest request) {
        if ("write-forbidden".equals(exception.getMessage())) {
            return error(request, HttpStatus.FORBIDDEN, "FORBIDDEN", "Você não tem permissão para esta ação.");
        }
        return error(request, HttpStatus.FORBIDDEN, "FORBIDDEN", "Não foi possível atender esta consulta.");
    }

    @ExceptionHandler(ValidationException.class)
    ResponseEntity<ApiError> validation(ValidationException exception, HttpServletRequest request) {
        return error(
                request,
                HttpStatus.BAD_REQUEST,
                "INVALID_REQUEST",
                exception.getMessage(),
                exception.fields());
    }

    @ExceptionHandler(VersionConflictException.class)
    ResponseEntity<ApiError> version(VersionConflictException exception, HttpServletRequest request) {
        return error(request, HttpStatus.CONFLICT, "VERSION_CONFLICT", exception.getMessage(), exception.fields());
    }

    @ExceptionHandler(AlreadyReversedException.class)
    ResponseEntity<ApiError> reversed(AlreadyReversedException exception, HttpServletRequest request) {
        return error(request, HttpStatus.CONFLICT, "ALREADY_REVERSED", exception.getMessage());
    }

    @ExceptionHandler(IdempotencyConflictException.class)
    ResponseEntity<ApiError> idempotency(IdempotencyConflictException exception, HttpServletRequest request) {
        return error(request, HttpStatus.CONFLICT, "IDEMPOTENCY_CONFLICT", exception.getMessage());
    }

    @ExceptionHandler({
        MethodArgumentTypeMismatchException.class,
        MissingServletRequestParameterException.class,
        MissingRequestHeaderException.class,
        HttpMessageNotReadableException.class,
        IllegalArgumentException.class
    })
    ResponseEntity<ApiError> badRequest(Exception exception, HttpServletRequest request) {
        return error(request, HttpStatus.BAD_REQUEST, "INVALID_REQUEST", "Identificador inválido.");
    }

    @ExceptionHandler(NoHandlerFoundException.class)
    ResponseEntity<ApiError> notFound(NoHandlerFoundException exception, HttpServletRequest request) {
        return error(request, HttpStatus.NOT_FOUND, "NOT_FOUND", "Não encontrado.");
    }

    private static ResponseEntity<ApiError> error(
            HttpServletRequest request, HttpStatus status, String code, String message) {
        return error(request, status, code, message, Map.of());
    }

    private static ResponseEntity<ApiError> error(
            HttpServletRequest request,
            HttpStatus status,
            String code,
            String message,
            Map<String, String> fields) {
        Object attribute = request.getAttribute(CorrelationFilter.ATTRIBUTE);
        String correlationId = attribute instanceof String value ? value : "unassigned";
        return ResponseEntity.status(status).body(new ApiError(code, message, correlationId, fields));
    }
}
