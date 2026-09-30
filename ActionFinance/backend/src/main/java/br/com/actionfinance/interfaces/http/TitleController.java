package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.TitleListQuery;
import br.com.actionfinance.application.finance.TitleService;
import br.com.actionfinance.application.finance.TitleView;
import br.com.actionfinance.application.finance.TitleWriteCommand;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.domain.TitleStatus;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.HistoryItem;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.HistoryResponse;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.TitleListResponse;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.TitleResponse;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.TitleSummaryResponse;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.TitleWriteRequest;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.VersionRequest;
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
import java.util.UUID;

@RestController
public class TitleController {

    private final TitleService titles;

    public TitleController(TitleService titles) {
        this.titles = titles;
    }

    @GetMapping("/api/v1/receivables")
    TitleListResponse listReceivables(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) LocalDate dueFrom,
            @RequestParam(required = false) LocalDate dueTo,
            @RequestParam(required = false) UUID categoryId,
            @RequestParam(required = false, defaultValue = "false") boolean overdueOnly,
            @RequestParam(required = false) String settlement,
            @RequestParam(required = false, defaultValue = "0") int page,
            @RequestParam(required = false, defaultValue = "20") int size,
            @RequestParam(required = false, defaultValue = "dueDate,id") String sort) {
        return list(principal, companyId, TitleDirection.RECEIVABLE, q, status, dueFrom, dueTo, categoryId, overdueOnly, settlement, page, size, sort);
    }

    @GetMapping("/api/v1/payables")
    TitleListResponse listPayables(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) LocalDate dueFrom,
            @RequestParam(required = false) LocalDate dueTo,
            @RequestParam(required = false) UUID categoryId,
            @RequestParam(required = false, defaultValue = "false") boolean overdueOnly,
            @RequestParam(required = false) String settlement,
            @RequestParam(required = false, defaultValue = "0") int page,
            @RequestParam(required = false, defaultValue = "20") int size,
            @RequestParam(required = false, defaultValue = "dueDate,id") String sort) {
        return list(principal, companyId, TitleDirection.PAYABLE, q, status, dueFrom, dueTo, categoryId, overdueOnly, settlement, page, size, sort);
    }

    @GetMapping("/api/v1/receivables/{id}")
    TitleResponse getReceivable(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId, @PathVariable UUID id) {
        return TitleResponse.from(titles.get(principal, companyId, TitleDirection.RECEIVABLE, id), titles.businessDate());
    }

    @GetMapping("/api/v1/payables/{id}")
    TitleResponse getPayable(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId, @PathVariable UUID id) {
        return TitleResponse.from(titles.get(principal, companyId, TitleDirection.PAYABLE, id), titles.businessDate());
    }

    @GetMapping("/api/v1/receivables/{id}/history")
    HistoryResponse receivableHistory(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId, @PathVariable UUID id) {
        return history(principal, companyId, TitleDirection.RECEIVABLE, id);
    }

    @GetMapping("/api/v1/payables/{id}/history")
    HistoryResponse payableHistory(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId, @PathVariable UUID id) {
        return history(principal, companyId, TitleDirection.PAYABLE, id);
    }

    @PostMapping("/api/v1/receivables")
    TitleResponse createReceivable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false, defaultValue = "false") boolean register,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody TitleWriteRequest body) {
        return create(principal, companyId, TitleDirection.RECEIVABLE, register, idempotencyKey, body);
    }

    @PostMapping("/api/v1/payables")
    TitleResponse createPayable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false, defaultValue = "false") boolean register,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody TitleWriteRequest body) {
        return create(principal, companyId, TitleDirection.PAYABLE, register, idempotencyKey, body);
    }

    @PatchMapping("/api/v1/receivables/{id}")
    TitleResponse updateReceivable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestParam(required = false, defaultValue = "false") boolean register,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody TitleWriteRequest body) {
        return update(principal, companyId, TitleDirection.RECEIVABLE, id, register, idempotencyKey, body);
    }

    @PatchMapping("/api/v1/payables/{id}")
    TitleResponse updatePayable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestParam(required = false, defaultValue = "false") boolean register,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody TitleWriteRequest body) {
        return update(principal, companyId, TitleDirection.PAYABLE, id, register, idempotencyKey, body);
    }

    @PostMapping("/api/v1/receivables/{id}/confirm")
    TitleResponse confirmReceivable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody VersionRequest body) {
        return TitleResponse.from(
                titles.confirm(principal, companyId, TitleDirection.RECEIVABLE, id, body.version(), idempotencyKey),
                titles.businessDate());
    }

    @PostMapping("/api/v1/payables/{id}/confirm")
    TitleResponse confirmPayable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody VersionRequest body) {
        return TitleResponse.from(
                titles.confirm(principal, companyId, TitleDirection.PAYABLE, id, body.version(), idempotencyKey),
                titles.businessDate());
    }

    @PostMapping("/api/v1/receivables/{id}/cancel")
    TitleResponse cancelReceivable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody VersionRequest body) {
        return TitleResponse.from(
                titles.cancel(principal, companyId, TitleDirection.RECEIVABLE, id, body.version(), body.reason(), idempotencyKey),
                titles.businessDate());
    }

    @PostMapping("/api/v1/payables/{id}/cancel")
    TitleResponse cancelPayable(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody VersionRequest body) {
        return TitleResponse.from(
                titles.cancel(principal, companyId, TitleDirection.PAYABLE, id, body.version(), body.reason(), idempotencyKey),
                titles.businessDate());
    }

    private TitleListResponse list(
            ApplicationPrincipal principal,
            UUID companyId,
            TitleDirection direction,
            String q,
            String status,
            LocalDate dueFrom,
            LocalDate dueTo,
            UUID categoryId,
            boolean overdueOnly,
            String settlement,
            int page,
            int size,
            String sort) {
        if (!TitleListQuery.ALLOWED_SORT.contains(sort)) {
            throw new IllegalArgumentException("sort");
        }
        if (!TitleListQuery.ALLOWED_SIZES.contains(size) || page < 0) {
            throw new IllegalArgumentException("page");
        }
        if (dueFrom != null && dueTo != null && dueFrom.isAfter(dueTo)) {
            throw new IllegalArgumentException("due");
        }
        TitleStatus parsed = FinanceHttpModels.parseStatus(status);
        TitleListQuery query = new TitleListQuery(
                q,
                parsed,
                parsed == null,
                dueFrom,
                dueTo,
                categoryId,
                overdueOnly,
                FinanceHttpModels.parseFinancial(settlement, parsed),
                page,
                size);
        TitleView.Page result = titles.list(principal, companyId, direction, query);
        return new TitleListResponse(
                result.items().stream().map(item -> TitleResponse.from(item, result.businessDate())).toList(),
                result.totalItems(),
                result.page(),
                result.size(),
                TitleSummaryResponse.from(result.summary()),
                result.businessDate());
    }

    private TitleResponse create(
            ApplicationPrincipal principal,
            UUID companyId,
            TitleDirection direction,
            boolean register,
            String idempotencyKey,
            TitleWriteRequest body) {
        TitleWriteCommand command = new TitleWriteCommand(
                body.description(),
                body.counterpartyId(),
                body.sourceReference(),
                body.amountMinor(),
                body.currency(),
                body.competenceDate(),
                body.dueDate(),
                body.categoryId(),
                register,
                body.version(),
                body.reason());
        return TitleResponse.from(titles.create(principal, companyId, direction, command, idempotencyKey), titles.businessDate());
    }

    private TitleResponse update(
            ApplicationPrincipal principal,
            UUID companyId,
            TitleDirection direction,
            UUID id,
            boolean register,
            String idempotencyKey,
            TitleWriteRequest body) {
        TitleWriteCommand command = new TitleWriteCommand(
                body.description(),
                body.counterpartyId(),
                body.sourceReference(),
                body.amountMinor(),
                body.currency(),
                body.competenceDate(),
                body.dueDate(),
                body.categoryId(),
                register,
                body.version(),
                body.reason());
        return TitleResponse.from(titles.update(principal, companyId, direction, id, command, idempotencyKey), titles.businessDate());
    }

    private HistoryResponse history(ApplicationPrincipal principal, UUID companyId, TitleDirection direction, UUID id) {
        return new HistoryResponse(
                titles.history(principal, companyId, direction, id).stream()
                        .map(item -> new HistoryItem(
                                item.id(),
                                item.titleVersion(),
                                item.action().name(),
                                item.actorId(),
                                item.actorDisplayName(),
                                item.occurredAt(),
                                item.reason(),
                                item.changesJson()))
                        .toList());
    }
}
