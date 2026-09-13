package br.com.segsense.inbound.http;

import br.com.segsense.application.correlation.CorrelationContext;
import br.com.segsense.domain.correlation.CorrelationIds;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class CorrelationFilter extends OncePerRequestFilter {

  @Override
  protected boolean shouldNotFilter(HttpServletRequest request) {
    String uri = request.getRequestURI();
    String contextPath = request.getContextPath() == null ? "" : request.getContextPath();
    String path = uri == null ? "" : uri.substring(contextPath.length());
    return !path.startsWith("/api/");
  }

  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
      throws ServletException, IOException {
    UUID correlationId = CorrelationIds.resolve(request.getHeader(CorrelationContext.HTTP_HEADER));
    CorrelationContext.set(correlationId);
    MDC.put(CorrelationContext.MDC_KEY, correlationId.toString());
    response.setHeader(CorrelationContext.HTTP_HEADER, correlationId.toString());
    try {
      filterChain.doFilter(request, response);
    } finally {
      MDC.remove(CorrelationContext.MDC_KEY);
      CorrelationContext.clear();
    }
  }
}
