package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.SettlementService;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.ReversalWriteRequest;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.SettlementResponse;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.SettlementWriteRequest;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
public class SettlementController {

    private final SettlementService settlements;

    public SettlementController(SettlementService settlements) {
        this.settlements = settlements;
    }

    @GetMapping("/api/v1/receivables/{id}/settlements")
    List<SettlementResponse> listReceivable(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId, @PathVariable UUID id) {
        return settlements.list(principal, companyId, TitleDirection.RECEIVABLE, id).stream()
                .map(SettlementResponse::from)
                .toList();
    }

    @GetMapping("/api/v1/payables/{id}/settlements")
    List<SettlementResponse> listPayable(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId, @PathVariable UUID id) {
        return settlements.list(principal, companyId, TitleDirection.PAYABLE, id).stream()
                .map(SettlementResponse::from)
                .toList();
    }

    @PostMapping("/api/v1/receivables/{id}/settlements")
    SettlementResponse recordReceivable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody SettlementWriteRequest body) {
        return SettlementResponse.from(
                settlements.record(
                        principal,
                        companyId,
                        TitleDirection.RECEIVABLE,
                        id,
                        body.accountId(),
                        body.amountMinor(),
                        body.effectiveDate(),
                        body.method(),
                        body.note(),
                        body.version(),
                        idempotencyKey));
    }

    @PostMapping("/api/v1/payables/{id}/settlements")
    SettlementResponse recordPayable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody SettlementWriteRequest body) {
        return SettlementResponse.from(
                settlements.record(
                        principal,
                        companyId,
                        TitleDirection.PAYABLE,
                        id,
                        body.accountId(),
                        body.amountMinor(),
                        body.effectiveDate(),
                        body.method(),
                        body.note(),
                        body.version(),
                        idempotencyKey));
    }

    @GetMapping("/api/v1/settlements/{id}")
    SettlementResponse get(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId, @PathVariable UUID id) {
        return SettlementResponse.from(settlements.get(principal, companyId, id));
    }

    @PostMapping("/api/v1/settlements/{id}/reversal")
    SettlementResponse reverse(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody ReversalWriteRequest body) {
        return SettlementResponse.from(
                settlements.reverse(
                        principal,
                        companyId,
                        id,
                        body.effectiveDate(),
                        body.reason(),
                        body.version(),
                        idempotencyKey));
    }
}
