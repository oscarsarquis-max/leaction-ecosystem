package br.com.actionfinance.application;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

public record DemoPrincipal(
        UUID actorId,
        String displayName,
        Set<UUID> authorizedCompanyIds,
        Set<String> permissions,
        Map<UUID, Set<String>> permissionsByCompany)
        implements ApplicationPrincipal {

    /**
     * Demo adaptation: every authorized company of this persona receives the same
     * permission set. No extra powers beyond the catalog role.
     */
    public DemoPrincipal(UUID actorId, String displayName, Set<UUID> authorizedCompanyIds, Set<String> permissions) {
        this(actorId, displayName, authorizedCompanyIds, permissions, uniform(authorizedCompanyIds, permissions));
    }

    private static Map<UUID, Set<String>> uniform(Set<UUID> companies, Set<String> permissions) {
        Map<UUID, Set<String>> byCompany = new LinkedHashMap<>();
        Set<String> copy = Set.copyOf(permissions);
        for (UUID companyId : companies) {
            byCompany.put(companyId, copy);
        }
        return Map.copyOf(byCompany);
    }
}
