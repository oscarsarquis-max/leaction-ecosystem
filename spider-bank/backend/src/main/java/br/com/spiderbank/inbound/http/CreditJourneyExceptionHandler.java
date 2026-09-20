package br.com.spiderbank.inbound.http;

import br.com.spiderbank.application.CreditJourneyException;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class CreditJourneyExceptionHandler {

  @ExceptionHandler(CreditJourneyException.class)
  public ResponseEntity<Map<String, Object>> handle(CreditJourneyException exception) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("errorCode", exception.errorCode());
    body.put("message", exception.getMessage());
    body.put("retryable", exception.retryable());
    body.put("creditDecision", "NONE");
    return ResponseEntity.status(exception.status()).body(body);
  }
}
