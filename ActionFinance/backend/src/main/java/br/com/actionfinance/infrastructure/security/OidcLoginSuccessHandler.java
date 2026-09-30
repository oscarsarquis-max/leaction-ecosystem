package br.com.actionfinance.infrastructure.security;

import br.com.actionfinance.application.identity.AccessState;
import br.com.actionfinance.application.identity.IdentityAuthorizationService;
import br.com.actionfinance.configuration.ActionFinanceProperties;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.security.web.context.SecurityContextRepository;

import java.io.IOException;

public class OidcLoginSuccessHandler implements AuthenticationSuccessHandler {

    private final IdentityAuthorizationService identities;
    private final ActionFinanceProperties properties;
    private final SecurityContextRepository securityContextRepository = new HttpSessionSecurityContextRepository();

    public OidcLoginSuccessHandler(
            IdentityAuthorizationService identities, ActionFinanceProperties properties) {
        this.identities = identities;
        this.properties = properties;
    }

    @Override
    public void onAuthenticationSuccess(
            HttpServletRequest request, HttpServletResponse response, Authentication authentication)
            throws IOException {
        if (!(authentication.getPrincipal() instanceof OidcUser oidcUser)) {
            response.sendRedirect(absolute("/?login=failed"));
            return;
        }
        request.changeSessionId();
        var principal =
                identities.resolve(oidcUser.getIssuer().toString(), oidcUser.getSubject(), displayName(oidcUser));
        var local =
                new UsernamePasswordAuthenticationToken(
                        principal,
                        authentication.getCredentials(),
                        principal.permissions().stream().map(SimpleGrantedAuthority::new).toList());
        var context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(local);
        SecurityContextHolder.setContext(context);
        securityContextRepository.saveContext(context, request, response);
        String path = principal.accessState() == AccessState.READY ? "/receivables" : "/access-pending";
        response.sendRedirect(absolute(path));
    }

    private String absolute(String path) {
        String origin = properties.getPublicOrigin().replaceAll("/$", "");
        return origin + path;
    }

    private static String displayName(OidcUser oidcUser) {
        if (oidcUser.getFullName() != null && !oidcUser.getFullName().isBlank()) {
            return oidcUser.getFullName();
        }
        if (oidcUser.getPreferredUsername() != null && !oidcUser.getPreferredUsername().isBlank()) {
            return oidcUser.getPreferredUsername();
        }
        return "Conta autenticada";
    }
}
