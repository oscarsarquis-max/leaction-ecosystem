package br.com.actionfinance.infrastructure.security;

import br.com.actionfinance.application.DemoPrincipal;
import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.configuration.ActionFinanceProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpHeaders;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.codec.Utf8;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.security.MessageDigest;
import java.util.List;

@Component
@Profile("local-demo")
public class DemoBearerAuthenticationFilter extends OncePerRequestFilter {

    private final ActionFinanceProperties properties;

    public DemoBearerAuthenticationFilter(ActionFinanceProperties properties) {
        this.properties = properties;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        if (!properties.getDemoAuth().isEnabled()) {
            filterChain.doFilter(request, response);
            return;
        }
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header != null && header.regionMatches(true, 0, "Bearer ", 0, 7)) {
            String presented = header.substring(7).trim();
            DemoPrincipal principal = match(presented);
            if (principal != null) {
                var authentication = new UsernamePasswordAuthenticationToken(
                        principal,
                        "demo",
                        principal.permissions().stream().map(SimpleGrantedAuthority::new).toList());
                authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                SecurityContextHolder.getContext().setAuthentication(authentication);
            }
        }
        rejectClientPrivilegeHeaders(request);
        filterChain.doFilter(request, response);
    }

    private DemoPrincipal match(String presented) {
        var demo = properties.getDemoAuth();
        if (constantEquals(presented, demo.getOperatorAToken())) {
            return DemoPrincipalCatalog.OPERATOR_COMPANY_A;
        }
        if (constantEquals(presented, demo.getViewerAToken())) {
            return DemoPrincipalCatalog.VIEWER_COMPANY_A;
        }
        if (constantEquals(presented, demo.getViewerBToken())) {
            return DemoPrincipalCatalog.VIEWER_COMPANY_B;
        }
        if (constantEquals(presented, demo.getOperatorMultiToken())) {
            return DemoPrincipalCatalog.OPERATOR_MULTI_AC;
        }
        if (constantEquals(presented, demo.getMixedAbToken())) {
            return DemoPrincipalCatalog.MIXED_A_OPERATOR_B_VIEWER;
        }
        return null;
    }

    private static boolean constantEquals(String left, String right) {
        if (left == null || right == null || left.isBlank() || right.isBlank()) {
            return false;
        }
        return MessageDigest.isEqual(Utf8.encode(left), Utf8.encode(right));
    }

    private static void rejectClientPrivilegeHeaders(HttpServletRequest request) {
        List<String> forbidden = List.of("X-Actor-Id", "X-Company-Id", "X-Role", "X-Permissions");
        for (String name : forbidden) {
            if (request.getHeader(name) != null) {
                request.setAttribute("actionfinance.ignored-privilege-header", name);
            }
        }
    }
}
