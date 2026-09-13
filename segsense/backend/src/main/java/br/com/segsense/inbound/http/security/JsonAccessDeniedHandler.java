package br.com.segsense.inbound.http.security;

import br.com.segsense.inbound.http.error.ApiErrorCodes;
import br.com.segsense.inbound.http.error.SecurityErrorResponder;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

@Component
public class JsonAccessDeniedHandler implements AccessDeniedHandler {

  private final SecurityErrorResponder responder;

  public JsonAccessDeniedHandler(SecurityErrorResponder responder) {
    this.responder = responder;
  }

  @Override
  public void handle(
      HttpServletRequest request, HttpServletResponse response, AccessDeniedException exception)
      throws IOException {
    responder.write(
        request,
        response,
        HttpStatus.FORBIDDEN.value(),
        ApiErrorCodes.ACCESS_DENIED,
        "Acesso não autorizado para esta operação.");
  }
}
