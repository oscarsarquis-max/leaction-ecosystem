package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.integration.ExternalLookupService;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.ExternalLookupRequest;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.ExternalLookupResponse;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.UUID;

@RestController
public class ExternalLookupController {

    private final ExternalLookupService lookups;

    public ExternalLookupController(ExternalLookupService lookups) {
        this.lookups = lookups;
    }

    @GetMapping("/api/v1/receivables/{id}/pay-lookup")
    ExternalLookupResponse getReceivable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id) {
        return lookups
                .current(principal, companyId, TitleDirection.RECEIVABLE, id)
                .map(ExternalLookupResponse::from)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    }

    @GetMapping("/api/v1/payables/{id}/pay-lookup")
    ExternalLookupResponse getPayable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id) {
        return lookups
                .current(principal, companyId, TitleDirection.PAYABLE, id)
                .map(ExternalLookupResponse::from)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    }

    @PostMapping("/api/v1/receivables/{id}/pay-lookup")
    @ResponseStatus(HttpStatus.OK)
    ExternalLookupResponse consultReceivable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestBody ExternalLookupRequest request) {
        return ExternalLookupResponse.from(
                lookups.consult(
                        principal,
                        companyId,
                        TitleDirection.RECEIVABLE,
                        id,
                        request == null ? null : request.externalReference()));
    }

    @PostMapping("/api/v1/payables/{id}/pay-lookup")
    @ResponseStatus(HttpStatus.OK)
    ExternalLookupResponse consultPayable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestBody ExternalLookupRequest request) {
        return ExternalLookupResponse.from(
                lookups.consult(
                        principal,
                        companyId,
                        TitleDirection.PAYABLE,
                        id,
                        request == null ? null : request.externalReference()));
    }
}
