package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.treasury.TreasuryService;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.Map;
import java.util.UUID;

@RestController
public class TreasuryController {

    private final TreasuryService treasury;

    public TreasuryController(TreasuryService treasury) {
        this.treasury = treasury;
    }

    @GetMapping("/api/v1/treasury/summary")
    Map<String, Object> summary(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) LocalDate from,
            @RequestParam(required = false) LocalDate to) {
        return treasury.summary(principal, companyId, from, to);
    }

    @GetMapping("/api/v1/treasury/agenda")
    Map<String, Object> agenda(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) String bucket,
            @RequestParam(required = false) String direction,
            @RequestParam(required = false, defaultValue = "0") int page,
            @RequestParam(required = false, defaultValue = "20") int size) {
        return treasury.agenda(principal, companyId, bucket, direction, page, size);
    }

    @GetMapping("/api/v1/treasury/calendar")
    Map<String, Object> calendar(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) String month,
            @RequestParam(required = false) String direction,
            @RequestParam(required = false) String day,
            @RequestParam(required = false) String focus,
            @RequestParam(required = false, defaultValue = "0") int page,
            @RequestParam(required = false, defaultValue = "8") int size) {
        return treasury.calendar(principal, companyId, month, direction, day, focus, page, size);
    }
}
