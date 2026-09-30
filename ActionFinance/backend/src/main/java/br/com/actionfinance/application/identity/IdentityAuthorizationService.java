package br.com.actionfinance.application.identity;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.CompanyCatalog;
import br.com.actionfinance.application.finance.CompanyView;
import br.com.actionfinance.infrastructure.persistence.JdbcIdentityRepository;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class IdentityAuthorizationService {

    private final JdbcIdentityRepository identities;
    private final CompanyCatalog companies;

    public IdentityAuthorizationService(JdbcIdentityRepository identities, CompanyCatalog companies) {
        this.identities = identities;
        this.companies = companies;
    }

    public ApplicationPrincipal resolve(String issuer, String subject, String displayName) {
        return identities
                .findIdentity(issuer, subject)
                .map(identity -> resolveUser(identity.userId(), issuer, subject))
                .orElseGet(() -> new UnprovisionedPrincipal(safeName(displayName), issuer, subject));
    }

    public ApplicationPrincipal resolveUser(UUID userId, String issuer, String subject) {
        var user = identities.findUser(userId).orElseThrow(() -> new IllegalStateException("Linked user missing."));
        if (user.status() == UserStatus.BLOCKED) {
            return new ApplicationUserPrincipal(
                    user.id(),
                    user.displayName(),
                    Set.of(),
                    Set.of(),
                    Map.of(),
                    true,
                    issuer,
                    subject);
        }
        List<IdentityRecords.Membership> memberships = identities.listActiveMemberships(user.id());
        Set<UUID> companyIds = new LinkedHashSet<>();
        Map<UUID, Set<String>> byCompany = new LinkedHashMap<>();
        Set<String> navigation = new LinkedHashSet<>();
        for (IdentityRecords.Membership membership : memberships) {
            companyIds.add(membership.companyId());
            Set<String> granted = FinancePermissions.forRole(membership.role());
            byCompany.put(membership.companyId(), granted);
            navigation.addAll(granted);
        }
        return new ApplicationUserPrincipal(
                user.id(),
                user.displayName(),
                Set.copyOf(companyIds),
                Set.copyOf(navigation),
                Map.copyOf(byCompany),
                false,
                issuer,
                subject);
    }

    public List<AuthorizedCompany> authorizedCompanies(ApplicationPrincipal principal) {
        if (principal.authorizedCompanyIds().isEmpty()) {
            return List.of();
        }
        List<CompanyView> views = companies.findByIds(List.copyOf(principal.authorizedCompanyIds()));
        return views.stream()
                .map(
                        company -> {
                            Set<String> granted = principal.permissionsFor(company.id());
                            MembershipRole role =
                                    granted.contains(FinancePermissions.TITLES_WRITE)
                                            ? MembershipRole.OPERATOR
                                            : MembershipRole.VIEWER;
                            return new AuthorizedCompany(
                                    company.id(),
                                    company.tenantId(),
                                    company.code(),
                                    company.name(),
                                    company.active(),
                                    company.demo(),
                                    company.businessTimezone(),
                                    role,
                                    granted);
                        })
                .toList();
    }

    private static String safeName(String displayName) {
        if (displayName == null || displayName.isBlank()) {
            return "Conta autenticada";
        }
        return displayName.trim();
    }
}
