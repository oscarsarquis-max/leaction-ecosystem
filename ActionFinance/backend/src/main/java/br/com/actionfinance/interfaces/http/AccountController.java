package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.AccountService;
import br.com.actionfinance.application.finance.MovementView;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.AccountResponse;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.AccountWriteRequest;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.MovementPageResponse;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.MovementResponse;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import java.util.UUID;

@RestController
public class AccountController {

    private static final Set<Integer> SIZES = Set.of(20, 50);

    private final AccountService accounts;

    public AccountController(AccountService accounts) {
        this.accounts = accounts;
    }

    @GetMapping("/api/v1/financial-accounts")
    List<AccountResponse> list(@AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId) {
        return accounts.list(principal, companyId).stream().map(AccountResponse::from).toList();
    }

    @GetMapping("/api/v1/financial-accounts/{id}")
    AccountResponse get(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId, @PathVariable UUID id) {
        return AccountResponse.from(accounts.get(principal, companyId, id));
    }

    @PostMapping("/api/v1/financial-accounts")
    AccountResponse create(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody AccountWriteRequest body) {
        return AccountResponse.from(
                accounts.create(
                        principal,
                        companyId,
                        body.name(),
                        body.type(),
                        body.openedOn(),
                        body.openingBalanceMinor(),
                        idempotencyKey));
    }

    @PatchMapping("/api/v1/financial-accounts/{id}")
    AccountResponse update(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody AccountWriteRequest body) {
        return AccountResponse.from(
                accounts.update(principal, companyId, id, body.name(), body.active(), body.version(), idempotencyKey));
    }

    @GetMapping("/api/v1/financial-accounts/{id}/movements")
    MovementPageResponse movements(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestParam(required = false) LocalDate from,
            @RequestParam(required = false) LocalDate to,
            @RequestParam(required = false, defaultValue = "0") int page,
            @RequestParam(required = false, defaultValue = "20") int size) {
        if (!SIZES.contains(size) || page < 0) {
            throw new IllegalArgumentException("page");
        }
        MovementView.Page result = accounts.movements(principal, companyId, id, from, to, page, size);
        return new MovementPageResponse(
                result.items().stream()
                        .map(item -> new MovementResponse(
                                item.id(),
                                item.kind().name(),
                                item.effectiveDate(),
                                item.recordedAt(),
                                item.recordedBy(),
                                item.description(),
                                item.inflowMinor().toPlainString(),
                                item.outflowMinor().toPlainString(),
                                item.balanceAfterMinor().toPlainString(),
                                item.settlementId(),
                                item.reversalId()))
                        .toList(),
                result.totalItems(),
                result.page(),
                result.size(),
                result.previousBalanceMinor().toPlainString(),
                result.periodEndBalanceMinor().toPlainString(),
                result.currentBalanceMinor().toPlainString(),
                result.from(),
                result.to());
    }
}
