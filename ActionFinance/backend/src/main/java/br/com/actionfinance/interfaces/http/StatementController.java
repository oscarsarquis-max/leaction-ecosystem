package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.statement.StatementService;
import br.com.actionfinance.application.statement.StatementService.ConfirmView;
import br.com.actionfinance.application.statement.StatementService.LineView;
import br.com.actionfinance.application.statement.StatementService.LinkView;
import br.com.actionfinance.application.statement.StatementService.PreviewView;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@RestController
public class StatementController {

    private static final Set<Integer> SIZES = Set.of(20, 50);

    private final StatementService statements;

    public StatementController(StatementService statements) {
        this.statements = statements;
    }

    @GetMapping("/api/v1/statement-links")
    List<LinkView> links(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) UUID accountId) {
        return statements.links(principal, companyId, accountId);
    }

    @PostMapping("/api/v1/statement-links")
    LinkView link(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestBody LinkRequest body) {
        return statements.link(principal, companyId, body.accountId(), body.externalRef(), body.provenance());
    }

    @PostMapping("/api/v1/statement-previews")
    PreviewView preview(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam UUID accountId,
            @RequestParam("file") MultipartFile file) throws IOException {
        return statements.preview(principal, companyId, accountId, file.getOriginalFilename(), file.getBytes());
    }

    @PostMapping("/api/v1/statement-previews/{id}/identify")
    PreviewView identify(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestBody IdentifyRequest body) {
        return statements.identify(principal, companyId, id, body.previewToken());
    }

    @PostMapping("/api/v1/statement-previews/{id}/confirm")
    ConfirmView confirm(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody ConfirmRequest body) {
        return statements.confirm(
                principal, companyId, id, body.previewToken(), body.lineNumbers(), body.accountEvidence(), idempotencyKey);
    }

    @PostMapping("/api/v1/statement-batches/{id}/withdraw")
    void withdraw(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestBody WithdrawRequest body) {
        statements.withdraw(principal, companyId, id, body.reason());
    }

    @GetMapping("/api/v1/statement-batches/{id}")
    Map<String, Object> batch(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id) {
        return statements.batch(principal, companyId, id);
    }

    @GetMapping("/api/v1/statement-batches")
    List<Map<String, Object>> batches(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) UUID accountId) {
        return statements.batches(principal, companyId, accountId);
    }

    @GetMapping("/api/v1/statement-lines")
    Map<String, Object> lines(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) UUID accountId,
            @RequestParam(required = false) LocalDate from,
            @RequestParam(required = false) LocalDate to,
            @RequestParam(required = false) String direction,
            @RequestParam(required = false) String eventKind,
            @RequestParam(required = false) String importStatus,
            @RequestParam(required = false) String suggestion,
            @RequestParam(required = false) String q,
            @RequestParam(required = false, defaultValue = "0") int page,
            @RequestParam(required = false, defaultValue = "20") int size) {
        if (!SIZES.contains(size) || page < 0) {
            throw new IllegalArgumentException("page");
        }
        return statements.lines(principal, companyId, accountId, from, to, direction, eventKind, importStatus, suggestion, q, page, size);
    }

    @GetMapping("/api/v1/statement-lines/{id}")
    LineView line(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id) {
        return statements.line(principal, companyId, id);
    }

    public record LinkRequest(UUID accountId, String externalRef, String provenance) {}

    public record IdentifyRequest(String previewToken) {}

    public record ConfirmRequest(String previewToken, List<Integer> lineNumbers, String accountEvidence) {}

    public record WithdrawRequest(String reason) {}
}
