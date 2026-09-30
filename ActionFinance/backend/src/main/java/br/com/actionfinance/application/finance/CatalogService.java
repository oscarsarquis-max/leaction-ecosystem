package br.com.actionfinance.application.finance;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.CatalogRecords.CategoryView;
import br.com.actionfinance.application.finance.CatalogRecords.CounterpartyView;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import br.com.actionfinance.domain.CategoryDirection;
import br.com.actionfinance.domain.CounterpartyRole;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.infrastructure.persistence.JdbcCatalogRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Service
public class CatalogService {

    private final CompanyAccessService access;
    private final JdbcCatalogRepository catalogs;
    private final Clock clock;

    public CatalogService(CompanyAccessService access, JdbcCatalogRepository catalogs, Clock clock) {
        this.access = access;
        this.catalogs = catalogs;
        this.clock = clock;
    }

    public List<CounterpartyView> listCounterparties(ApplicationPrincipal principal, UUID companyId) {
        return catalogs.listCounterparties(readable(principal, companyId));
    }

    public List<CategoryView> listCategories(ApplicationPrincipal principal, UUID companyId) {
        return catalogs.listCategories(readable(principal, companyId));
    }

    @Transactional
    public CounterpartyView createCounterparty(
            ApplicationPrincipal principal, UUID companyId, String name, CounterpartyRole role) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
        String trimmed = requireName(name, 160);
        Instant now = Instant.now(clock);
        UUID id = UUID.randomUUID();
        CounterpartyView row = new CounterpartyView(
                id,
                scope.tenantId(),
                scope.companyId(),
                "CTP-" + id,
                trimmed,
                role,
                true,
                1L,
                now,
                now);
        catalogs.insertCounterparty(row, principal.actorId());
        return row;
    }

    @Transactional
    public CounterpartyView updateCounterparty(
            ApplicationPrincipal principal, UUID companyId, UUID id, String name, Boolean active, Long version) {
        if (version == null) {
            throw ValidationException.of("version", "Versão é obrigatória.");
        }
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
        CounterpartyView current = catalogs.lockCounterparty(scope, id)
                .orElseThrow(() -> new SecurityException("catalog-hidden"));
        if (current.version() != version) {
            throw new VersionConflictException();
        }
        String trimmed = name == null ? null : requireName(name, 160);
        if (catalogs.updateCounterparty(scope, id, trimmed, active, version, Instant.now(clock), principal.actorId()) != 1) {
            throw new VersionConflictException();
        }
        return catalogs.findCounterparty(scope, id).orElseThrow();
    }

    @Transactional
    public CategoryView createCategory(
            ApplicationPrincipal principal, UUID companyId, String name, CategoryDirection direction) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
        String trimmed = requireName(name, 100);
        Instant now = Instant.now(clock);
        UUID id = UUID.randomUUID();
        CategoryView row = new CategoryView(
                id,
                scope.tenantId(),
                scope.companyId(),
                "CAT-" + id,
                trimmed,
                direction,
                true,
                1L,
                now,
                now);
        catalogs.insertCategory(row, principal.actorId());
        return row;
    }

    @Transactional
    public CategoryView updateCategory(
            ApplicationPrincipal principal, UUID companyId, UUID id, String name, Boolean active, Long version) {
        if (version == null) {
            throw ValidationException.of("version", "Versão é obrigatória.");
        }
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
        CategoryView current = catalogs.lockCategory(scope, id)
                .orElseThrow(() -> new SecurityException("catalog-hidden"));
        if (current.version() != version) {
            throw new VersionConflictException();
        }
        String trimmed = name == null ? null : requireName(name, 100);
        if (catalogs.updateCategory(scope, id, trimmed, active, version, Instant.now(clock), principal.actorId()) != 1) {
            throw new VersionConflictException();
        }
        return catalogs.findCategory(scope, id).orElseThrow();
    }

    public List<CounterpartyView> activeCompatibleCounterparties(
            ApplicationPrincipal principal, UUID companyId, TitleDirection direction) {
        return listCounterparties(principal, companyId).stream()
                .filter(CounterpartyView::active)
                .filter(item -> item.role().supports(direction))
                .toList();
    }

    public List<CategoryView> activeCompatibleCategories(
            ApplicationPrincipal principal, UUID companyId, TitleDirection direction) {
        return listCategories(principal, companyId).stream()
                .filter(CategoryView::active)
                .filter(item -> item.direction().supports(direction))
                .toList();
    }

    private AuthorizedScope readable(ApplicationPrincipal principal, UUID companyId) {
        CompanyView company = access.requireReadable(principal, companyId);
        return new AuthorizedScope(company.tenantId(), company.id());
    }


    private static String requireName(String name, int max) {
        String trimmed = name == null ? "" : name.trim();
        if (trimmed.isEmpty() || trimmed.length() > max) {
            throw ValidationException.of("name", "Nome é obrigatório e deve ter até " + max + " caracteres.");
        }
        return trimmed;
    }
}
