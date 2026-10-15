package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.PartyDirectoryService;
import br.com.actionfinance.application.finance.PartyImportService;
import br.com.actionfinance.application.finance.PartyRecords.ImportBatchView;
import br.com.actionfinance.application.finance.PartyRecords.PartyCandidate;
import br.com.actionfinance.application.finance.PartyRecords.PartyDetail;
import br.com.actionfinance.application.finance.PartyRecords.PartyPage;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyImportConfirmRequest;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyImportPreviewRequest;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyWriteRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/catalogs")
public class PartyDirectoryController {

    private final PartyDirectoryService parties;
    private final PartyImportService imports;

    public PartyDirectoryController(PartyDirectoryService parties, PartyImportService imports) {
        this.parties = parties;
        this.imports = imports;
    }

    @GetMapping("/parties")
    PartyPage list(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) String q,
            @RequestParam(required = false, defaultValue = "ALL") String relation,
            @RequestParam(required = false, defaultValue = "ALL") String status,
            @RequestParam(required = false) Boolean documentPending,
            @RequestParam(required = false, defaultValue = "ALL") String origin,
            @RequestParam(required = false, defaultValue = "0") int page,
            @RequestParam(required = false, defaultValue = "20") int size) {
        return parties.list(principal, companyId, q, relation, status, documentPending, origin, page, size);
    }

    @GetMapping("/party-candidates")
    List<PartyCandidate> candidates(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String documentCountry,
            @RequestParam(required = false) String documentType,
            @RequestParam(required = false) String documentNumber,
            @RequestParam(required = false) UUID exceptId) {
        return parties.candidates(principal, companyId, name, documentCountry, documentType, documentNumber, exceptId);
    }

    @GetMapping("/parties/{id}")
    PartyDetail get(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id) {
        return parties.get(principal, companyId, id);
    }

    @PostMapping("/parties")
    PartyDetail create(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestBody PartyWriteRequest body) {
        return parties.create(principal, companyId, body);
    }

    @PutMapping("/parties/{id}")
    PartyDetail update(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestBody PartyWriteRequest body) {
        return parties.update(principal, companyId, id, body);
    }

    @GetMapping("/party-imports/template")
    ResponseEntity<byte[]> template() {
        byte[] body = PartyImportService.TEMPLATE.getBytes(StandardCharsets.UTF_8);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"modelo-cadastros.csv\"")
                .contentType(new MediaType("text", "csv", StandardCharsets.UTF_8))
                .body(body);
    }

    @PostMapping("/party-imports")
    ImportBatchView preview(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestBody PartyImportPreviewRequest body) {
        return imports.preview(principal, companyId, body);
    }

    @GetMapping("/party-imports/{id}")
    ImportBatchView getImport(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id) {
        return imports.get(principal, companyId, id);
    }

    @PostMapping("/party-imports/{id}/confirm")
    ImportBatchView confirm(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestBody PartyImportConfirmRequest body) {
        return imports.confirm(principal, companyId, id, body);
    }
}
