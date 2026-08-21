package br.com.banco.spider.integration.inbound.http.canonical;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.annotation.Order;
import org.springframework.core.codec.DecodingException;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.bind.support.WebExchangeBindException;
import org.springframework.web.server.ServerWebInputException;
import org.springframework.web.server.UnsupportedMediaTypeStatusException;

@RestControllerAdvice(basePackages = "br.com.banco.spider.integration.inbound.http.canonical")
@ConditionalOnProperty(name = "spider.canonical.http.enabled", havingValue = "true")
@Order(0)
public class CanonicalHttpExceptionHandler {

  private static final Logger log = LoggerFactory.getLogger(CanonicalHttpExceptionHandler.class);

  @ExceptionHandler({
    WebExchangeBindException.class,
    ServerWebInputException.class,
    DecodingException.class,
    IllegalArgumentException.class
  })
  public ResponseEntity<Map<String, String>> badRequest(Exception ex) {
    CanonicalError err = safe("HTTP_BAD_REQUEST", "Invalid request", ErrorCategory.VALIDATION);
    log.info("event=http_mapping_result status=400 errorId={} reasonCode=BAD_REQUEST", err.errorId());
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .contentType(MediaType.APPLICATION_JSON)
        .body(Map.of("code", err.code(), "errorId", err.errorId(), "message", err.message()));
  }

  @ExceptionHandler(UnsupportedMediaTypeStatusException.class)
  public ResponseEntity<Map<String, String>> unsupported(UnsupportedMediaTypeStatusException ex) {
    CanonicalError err = safe("HTTP_UNSUPPORTED_MEDIA", "Unsupported media type", ErrorCategory.VALIDATION);
    return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
        .body(Map.of("code", err.code(), "errorId", err.errorId(), "message", err.message()));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<Map<String, String>> internal(Exception ex) {
    CanonicalError err = safe("HTTP_INTERNAL", "Internal error", ErrorCategory.INTERNAL);
    log.info("event=http_mapping_result status=500 errorId={} reasonCode=INTERNAL", err.errorId());
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
        .body(Map.of("code", err.code(), "errorId", err.errorId(), "message", err.message()));
  }

  private static CanonicalError safe(String code, String message, ErrorCategory category) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(category)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("canonical_http", null, null, null))
        .build();
  }
}
