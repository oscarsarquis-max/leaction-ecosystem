package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.infrastructure.security.CognitoLogoutUrls;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

import java.io.IOException;

@Controller
@ConditionalOnProperty(name = "actionfinance.oidc.enabled", havingValue = "true")
public class CognitoLogoutController {

    private final ActionFinanceProperties properties;

    public CognitoLogoutController(ActionFinanceProperties properties) {
        this.properties = properties;
    }

    @GetMapping("/access/cognito-logout")
    public void leave(HttpServletResponse response) throws IOException {
        response.setHeader("Cache-Control", "no-store");
        String target = CognitoLogoutUrls.providerLogout(properties).orElse(null);
        if (target == null) {
            String origin = properties.getPublicOrigin() == null ? "" : properties.getPublicOrigin().replaceAll("/$", "");
            response.sendRedirect(origin + "/?login=failed");
            return;
        }
        response.sendRedirect(target);
    }
}
