package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.integration.PayReceiptSyncService;
import br.com.actionfinance.application.integration.PayReceiptViews.SyncResult;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.UUID;

@RestController
public class PayReceiptController {

    private final PayReceiptSyncService receipts;

    public PayReceiptController(PayReceiptSyncService receipts) {
        this.receipts = receipts;
    }

    @GetMapping("/api/v1/pay-receipts")
    Map<String, Object> list(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) String environment) {
        return receipts.overview(principal, companyId, environment);
    }

    @GetMapping("/api/v1/pay-receipts/integrity")
    Map<String, Long> integrity(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId) {
        return receipts.financialCounts(principal, companyId);
    }

    @GetMapping("/api/v1/pay-receipts/{id}")
    Map<String, Object> detail(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id) {
        return receipts.detail(principal, companyId, id);
    }

    @PostMapping("/api/v1/pay-receipts/sync")
    SyncResult sync(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) String environment) {
        return receipts.synchronize(principal, companyId, environment);
    }
}
