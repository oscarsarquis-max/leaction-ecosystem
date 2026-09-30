package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.CatalogRecords.CategoryView;
import br.com.actionfinance.application.finance.CatalogRecords.CounterpartyView;
import br.com.actionfinance.application.finance.CatalogService;
import br.com.actionfinance.domain.CategoryDirection;
import br.com.actionfinance.domain.CounterpartyRole;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.CatalogWriteRequest;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/catalogs")
public class CatalogController {

    private final CatalogService catalogs;

    public CatalogController(CatalogService catalogs) {
        this.catalogs = catalogs;
    }

    @GetMapping("/counterparties")
    List<CounterpartyView> counterparties(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) TitleDirection compatibleWith) {
        if (compatibleWith != null) {
            return catalogs.activeCompatibleCounterparties(principal, companyId, compatibleWith);
        }
        return catalogs.listCounterparties(principal, companyId);
    }

    @PostMapping("/counterparties")
    CounterpartyView createCounterparty(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestBody CatalogWriteRequest body) {
        return catalogs.createCounterparty(principal, companyId, body.name(), CounterpartyRole.valueOf(body.role()));
    }

    @PatchMapping("/counterparties/{id}")
    CounterpartyView updateCounterparty(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestBody CatalogWriteRequest body) {
        return catalogs.updateCounterparty(principal, companyId, id, body.name(), body.active(), body.version());
    }

    @GetMapping("/categories")
    List<CategoryView> categories(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestParam(required = false) TitleDirection compatibleWith) {
        if (compatibleWith != null) {
            return catalogs.activeCompatibleCategories(principal, companyId, compatibleWith);
        }
        return catalogs.listCategories(principal, companyId);
    }

    @PostMapping("/categories")
    CategoryView createCategory(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @RequestBody CatalogWriteRequest body) {
        return catalogs.createCategory(principal, companyId, body.name(), CategoryDirection.valueOf(body.direction()));
    }

    @PatchMapping("/categories/{id}")
    CategoryView updateCategory(
            @AuthenticationPrincipal ApplicationPrincipal principal,
            @RequestParam UUID companyId,
            @PathVariable UUID id,
            @RequestBody CatalogWriteRequest body) {
        return catalogs.updateCategory(principal, companyId, id, body.name(), body.active(), body.version());
    }
}
