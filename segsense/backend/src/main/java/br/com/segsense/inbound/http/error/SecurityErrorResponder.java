package br.com.segsense.inbound.http.error;

import br.com.segsense.application.correlation.CorrelationContext;
import br.com.segsense.domain.correlation.CorrelationIds;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;

@Component
public class SecurityErrorResponder {

  public void write(HttpServletRequest request, HttpServletResponse response, int status, String code, String message)
      throws IOException {
    UUID correlationId = CorrelationContext.current();
    if (correlationId == null) {
      correlationId = CorrelationIds.resolve(request.getHeader(CorrelationContext.HTTP_HEADER));
    }
    String correlation = correlationId.toString();
    response.setStatus(status);
    response.setCharacterEncoding("UTF-8");
    response.setContentType(MediaType.APPLICATION_JSON_VALUE);
    response.setHeader(CorrelationContext.HTTP_HEADER, correlation);
    response.getOutputStream().write(ApiErrorBody.utf8(ApiError.of(code, message, correlation)));
  }
}
