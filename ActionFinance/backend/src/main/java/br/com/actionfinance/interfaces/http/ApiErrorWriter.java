package br.com.actionfinance.interfaces.http;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

public final class ApiErrorWriter {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private ApiErrorWriter() {}

    public static void write(
            HttpServletRequest request,
            HttpServletResponse response,
            HttpStatus status,
            String code,
            String message)
            throws IOException {
        if (response.isCommitted()) {
            return;
        }
        Object attribute = request.getAttribute(CorrelationFilter.ATTRIBUTE);
        String correlationId = attribute instanceof String value ? value : "unassigned";
        response.setStatus(status.value());
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        MAPPER.writeValue(response.getOutputStream(), new ApiError(code, message, correlationId));
    }
}
