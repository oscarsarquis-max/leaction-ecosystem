package br.com.segsense.inbound.http.link;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 5)
public class ContextLinkHeaderFilter extends OncePerRequestFilter {

  @Override
  protected boolean shouldNotFilter(HttpServletRequest request) {
    String path = path(request);
    return !(path.startsWith("/api/v1/public/context-links/")
        || path.contains("/opportunities/") && path.contains("/links"));
  }

  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
      throws ServletException, IOException {
    response.setHeader("Cache-Control", "no-store");
    response.setHeader("Pragma", "no-cache");
    response.setHeader("Referrer-Policy", "no-referrer");
    response.setHeader("X-Content-Type-Options", "nosniff");
    filterChain.doFilter(request, response);
  }

  private static String path(HttpServletRequest request) {
    String uri = request.getRequestURI();
    String contextPath = request.getContextPath() == null ? "" : request.getContextPath();
    return uri == null ? "" : uri.substring(contextPath.length());
  }
}
