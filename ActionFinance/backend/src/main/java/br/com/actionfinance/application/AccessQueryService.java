package br.com.actionfinance.application;

import br.com.actionfinance.application.finance.CompanyCatalog;
import br.com.actionfinance.application.finance.CompanyView;
import br.com.actionfinance.application.identity.AuthorizedCompany;
import br.com.actionfinance.application.identity.IdentityAuthorizationService;
import br.com.actionfinance.application.identity.OidcBoundPrincipal;

import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class AccessQueryService {

    public record AccessProfile(
            UUID actorId,
            String displayName,
            String accessState,
            String issuer,
            String subject,
            Set<UUID> companies,
            Set<String> permissions,
            Map<UUID, Set<String>> permissionsByCompany,
            List<CompanyView> authorizedCompanies,
            List<AuthorizedCompany> authorizedCompanyDetails) {}

    public record CompanyContext(
            UUID companyId,
            UUID tenantId,
            String name,
            boolean active,
            boolean demo,
            String businessTimezone,
            String technicalLabel) {}

    private final CompanyCatalog companies;
    private final IdentityAuthorizationService identities;

    public AccessQueryService(CompanyCatalog companies, IdentityAuthorizationService identities) {
        this.companies = companies;
        this.identities = identities;
    }

    public AccessProfile me(ApplicationPrincipal principal) {
        List<CompanyView> views =
                principal.authorizedCompanyIds().isEmpty()
                        ? List.of()
                        : companies.findByIds(List.copyOf(principal.authorizedCompanyIds()));
        String issuer = principal instanceof OidcBoundPrincipal bound ? bound.issuer() : null;
        String subject = principal instanceof OidcBoundPrincipal bound ? bound.subject() : null;
        return new AccessProfile(
                principal.actorId(),
                principal.displayName(),
                principal.accessState().name(),
                issuer,
                subject,
                principal.authorizedCompanyIds(),
                principal.permissions(),
                principal.permissionsByCompany(),
                views,
                identities.authorizedCompanies(principal));
    }

    public CompanyContext context(ApplicationPrincipal principal, UUID companyId) {
        if (!principal.canAccess(companyId)) {
            throw new SecurityException("company-forbidden");
        }
        CompanyView company =
                companies.findById(companyId).orElseThrow(() -> new SecurityException("company-forbidden"));
        return new CompanyContext(
                company.id(),
                company.tenantId(),
                company.name(),
                company.active(),
                company.demo(),
                company.businessTimezone(),
                company.name());
    }
}
