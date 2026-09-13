package br.com.segsense.inbound.http.link;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class PublicTokenRedactingFilter extends OncePerRequestFilter {

  static final String PREFIX = "/api/v1/public/context-links/";
  static final String MDC_PATH = "sanitizedPath";

  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
      throws ServletException, IOException {
    MDC.put(MDC_PATH, redact(request.getRequestURI()));
    try {
      filterChain.doFilter(request, response);
    } finally {
      MDC.remove(MDC_PATH);
    }
  }

  static String redact(String value) {
    if (value == null) {
      return null;
    }
    int index = value.indexOf(PREFIX);
    if (index < 0) {
      return value;
    }
    int start = index + PREFIX.length();
    int end = start;
    while (end < value.length()) {
      char current = value.charAt(end);
      if (current == '/' || current == '?' || current == '#') {
        break;
      }
      end++;
    }
    if (end == start) {
      return value;
    }
    return value.substring(0, start) + "[redacted]" + value.substring(end);
  }
}
