package br.com.actionfinance.interfaces.http;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
@ConditionalOnProperty(name = "actionfinance.oidc.enabled", havingValue = "true")
public class SpaController {

    @GetMapping({
        "/",
        "/receivables",
        "/receivables/",
        "/payables",
        "/payables/",
        "/financial-accounts",
        "/financial-accounts/",
        "/catalogs",
        "/catalogs/",
        "/access-pending"
    })
    public String applicationShell() {
        return "forward:/index.html";
    }

    @GetMapping({
        "/receivables/{*path}",
        "/payables/{*path}",
        "/financial-accounts/{*path}",
        "/catalogs/{*path}"
    })
    public String applicationDeepLink() {
        return "forward:/index.html";
    }
}
