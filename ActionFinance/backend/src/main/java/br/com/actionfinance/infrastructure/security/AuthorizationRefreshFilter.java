package br.com.actionfinance.infrastructure.security;

import br.com.actionfinance.application.identity.IdentityAuthorizationService;
import br.com.actionfinance.application.identity.OidcBoundPrincipal;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

public class AuthorizationRefreshFilter extends OncePerRequestFilter {

    private final IdentityAuthorizationService identities;

    public AuthorizationRefreshFilter(IdentityAuthorizationService identities) {
        this.identities = identities;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        var authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof OidcBoundPrincipal bound) {
            var fresh = identities.resolve(bound.issuer(), bound.subject(), bound.displayName());
            var refreshed =
                    new UsernamePasswordAuthenticationToken(
                            fresh,
                            authentication.getCredentials(),
                            fresh.permissions().stream().map(SimpleGrantedAuthority::new).toList());
            refreshed.setDetails(authentication.getDetails());
            SecurityContextHolder.getContext().setAuthentication(refreshed);
        }
        filterChain.doFilter(request, response);
    }
}
