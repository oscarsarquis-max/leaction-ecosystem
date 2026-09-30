package br.com.actionfinance.application.finance;

import br.com.actionfinance.application.ApplicationPrincipal;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class CompanyAccessService {

    private final CompanyCatalog companies;

    public CompanyAccessService(CompanyCatalog companies) {
        this.companies = companies;
    }

    public CompanyView requireReadable(ApplicationPrincipal principal, UUID companyId) {
        if (principal == null || !principal.canAccess(companyId)) {
            throw new SecurityException("company-forbidden");
        }
        return companies
                .findById(companyId)
                .orElseThrow(() -> new SecurityException("company-forbidden"));
    }

    public void requirePermission(ApplicationPrincipal principal, UUID companyId, String permission) {
        if (principal == null || !principal.hasPermission(companyId, permission)) {
            throw new SecurityException(writePermission(permission) ? "write-forbidden" : "company-forbidden");
        }
    }

    public AuthorizedScope requireWritable(ApplicationPrincipal principal, UUID companyId, String writePermission) {
        CompanyView company = requireReadable(principal, companyId);
        if (!company.active()) {
            throw new SecurityException("company-forbidden");
        }
        requirePermission(principal, companyId, writePermission);
        return new AuthorizedScope(company.tenantId(), company.id());
    }

    public AuthorizedScope requireActiveMembership(ApplicationPrincipal principal, UUID companyId) {
        CompanyView company = requireReadable(principal, companyId);
        if (!company.active()) {
            throw new SecurityException("company-forbidden");
        }
        return new AuthorizedScope(company.tenantId(), company.id());
    }

    private static boolean writePermission(String permission) {
        return permission != null
                && (permission.endsWith(":write") || permission.endsWith(":reverse"));
    }
}
