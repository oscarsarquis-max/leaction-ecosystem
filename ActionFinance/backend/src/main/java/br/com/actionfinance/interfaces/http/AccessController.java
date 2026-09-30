package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.AccessQueryService;
import br.com.actionfinance.application.ApplicationPrincipal;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/access")
public class AccessController {

    private final AccessQueryService accessQueryService;

    public AccessController(AccessQueryService accessQueryService) {
        this.accessQueryService = accessQueryService;
    }

    @GetMapping("/me")
    AccessQueryService.AccessProfile me(@AuthenticationPrincipal ApplicationPrincipal principal) {
        return accessQueryService.me(principal);
    }

    @GetMapping("/csrf")
    Map<String, String> csrf(CsrfToken token) {
        return Map.of(
                "headerName", token.getHeaderName(),
                "parameterName", token.getParameterName(),
                "token", token.getToken());
    }

    @GetMapping("/context")
    AccessQueryService.CompanyContext context(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId) {
        return accessQueryService.context(principal, companyId);
    }
}
