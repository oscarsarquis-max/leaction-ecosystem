package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.classification.AllocationMath;
import br.com.actionfinance.application.classification.ClassificationService;
import br.com.actionfinance.application.classification.ClassificationService.BookCommand;
import br.com.actionfinance.application.classification.ClassificationService.BookComponent;
import br.com.actionfinance.application.classification.ClassificationService.ClassifyCommand;
import br.com.actionfinance.application.classification.ClassificationService.ReferenceCommand;
import br.com.actionfinance.application.classification.ClassificationService.UndoCommand;
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
import java.util.Map;
import java.util.UUID;

@RestController
public class ClassificationController {

    private final ClassificationService classification;

    public ClassificationController(ClassificationService classification) {
        this.classification = classification;
    }

    @GetMapping("/api/v1/catalogs/initiatives")
    List<Map<String, Object>> initiatives(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId) {
        return classification.initiatives(principal, companyId);
    }

    @PostMapping("/api/v1/catalogs/initiatives")
    Map<String, Object> createInitiative(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody InitiativeRequest body) {
        return classification.createInitiative(principal, companyId, body.code(), body.name(), idempotencyKey);
    }

    @PatchMapping("/api/v1/catalogs/initiatives/{id}")
    Map<String, Object> updateInitiative(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody InitiativeUpdate body) {
        return classification.updateInitiative(principal, companyId, id, body.name(), body.active(), body.version(), body.reason(), idempotencyKey);
    }

    @PostMapping("/api/v1/catalogs/initiatives/application-map")
    Map<String, Object> mapApplication(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody MapRequest body) {
        return classification.mapApplication(principal, companyId, body.applicationCode(), body.initiativeId(), idempotencyKey);
    }

    @GetMapping("/api/v1/catalogs/allocation-rules")
    List<Map<String, Object>> rules(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId) {
        return classification.rules(principal, companyId);
    }

    @PostMapping("/api/v1/catalogs/allocation-rules")
    Map<String, Object> createRule(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody RuleRequest body) {
        return classification.createRule(principal, companyId, body.name(), body.validFrom(), body.validTo(), shares(body.shares()), idempotencyKey);
    }

    @PostMapping("/api/v1/catalogs/allocation-rules/{id}/versions")
    Map<String, Object> addVersion(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody RuleRequest body) {
        return classification.addRuleVersion(principal, companyId, id, body.validFrom(), body.validTo(), shares(body.shares()), idempotencyKey);
    }

    @GetMapping("/api/v1/reconciliation")
    Map<String, Object> queue(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) UUID accountId,
            @RequestParam(required = false) LocalDate from,
            @RequestParam(required = false) LocalDate to,
            @RequestParam(required = false) String situation,
            @RequestParam(required = false) String q,
            @RequestParam(required = false, defaultValue = "0") int page,
            @RequestParam(required = false, defaultValue = "20") int size) {
        return classification.queue(principal, companyId, accountId, from, to, situation, q, page, size);
    }

    @GetMapping("/api/v1/reconciliation/search")
    Map<String, Object> search(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) UUID accountId,
            @RequestParam(required = false) String q) {
        return classification.search(principal, companyId, accountId, q);
    }

    @GetMapping("/api/v1/reconciliation/lines/{id}")
    Map<String, Object> detail(
            @AuthenticationPrincipal ApplicationPrincipal principal, @RequestParam UUID companyId, @PathVariable UUID id) {
        return classification.detail(principal, companyId, id);
    }

    @PostMapping("/api/v1/reconciliation/classifications")
    Map<String, Object> classify(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody ClassifyCommand body) {
        return classification.classify(principal, companyId, body, idempotencyKey);
    }

    @PostMapping("/api/v1/reconciliation/references")
    Map<String, Object> reference(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody ReferenceCommand body) {
        return classification.reference(principal, companyId, body, idempotencyKey);
    }

    @PostMapping("/api/v1/reconciliation/book")
    Map<String, Object> book(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody BookCommand body) {
        return classification.book(principal, companyId, body, idempotencyKey);
    }

    @PostMapping("/api/v1/reconciliation/undo")
    Map<String, Object> undo(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody UndoCommand body) {
        return classification.undo(principal, companyId, body, idempotencyKey);
    }

    @PostMapping("/api/v1/reconciliation/occurrences/{id}/note")
    Map<String, Object> note(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody NoteRequest body) {
        return classification.note(principal, companyId, id, body.categoryId(), body.note(), idempotencyKey);
    }

    private static List<AllocationMath.Share> shares(List<ShareRequest> shares) {
        if (shares == null) {
            return List.of();
        }
        return shares.stream().map(share -> new AllocationMath.Share(share.initiativeId().toString(), share.code(), share.basisPoints())).toList();
    }

    public record InitiativeRequest(String code, String name) {}

    public record InitiativeUpdate(String name, Boolean active, long version, String reason) {}

    public record MapRequest(String applicationCode, UUID initiativeId) {}

    public record ShareRequest(UUID initiativeId, String code, int basisPoints) {}

    public record RuleRequest(String name, LocalDate validFrom, LocalDate validTo, List<ShareRequest> shares) {}

    public record NoteRequest(UUID categoryId, String note) {}
}
