package br.com.segsense.inbound.http.consent;

import br.com.segsense.infrastructure.config.CorsAllowedOrigins;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class PublicMutationOriginFilter extends OncePerRequestFilter {

  private final String[] allowedOrigins;

  public PublicMutationOriginFilter(
      @Value("${segsense.cors.allowed-origin}") String allowedOrigin) {
    this.allowedOrigins = CorsAllowedOrigins.parse(allowedOrigin);
  }

  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
      throws ServletException, IOException {
    if (!isPublicMutation(request)) {
      filterChain.doFilter(request, response);
      return;
    }
    String origin = request.getHeader("Origin");
    if (origin != null && !CorsAllowedOrigins.allows(allowedOrigins, origin)) {
      reject(response);
      return;
    }
    String site = request.getHeader("Sec-Fetch-Site");
    if (site != null && "cross-site".equalsIgnoreCase(site)) {
      reject(response);
      return;
    }
    filterChain.doFilter(request, response);
  }

  private static boolean isPublicMutation(HttpServletRequest request) {
    String path = request.getRequestURI();
    if (path == null) {
      return false;
    }
    if (path.contains("/api/v1/public/demo/protection-journeys")
        || path.contains("/api/v1/public/demo/legacy-protection-journeys")
        || path.contains("/api/v1/public/demo/context-sources")
        || path.contains("/api/v1/public/demo/url-captures")) {
      return "POST".equalsIgnoreCase(request.getMethod());
    }
    if (!path.contains("/api/v1/public/context-links/")) {
      return false;
    }
    String method = request.getMethod();
    return "POST".equalsIgnoreCase(method) || "PUT".equalsIgnoreCase(method);
  }

  private static void reject(HttpServletResponse response) throws IOException {
    response.setStatus(HttpServletResponse.SC_FORBIDDEN);
    response.setContentType(MediaType.APPLICATION_JSON_VALUE);
    response.getWriter().write("{\"code\":\"ACCESS_DENIED\",\"message\":\"Origem não permitida.\"}");
  }
}
