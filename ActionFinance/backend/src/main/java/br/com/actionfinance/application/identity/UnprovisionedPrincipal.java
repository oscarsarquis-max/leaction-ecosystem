package br.com.actionfinance.application.identity;

import java.io.Serial;
import java.io.Serializable;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

public record UnprovisionedPrincipal(String displayName, String issuer, String subject)
        implements OidcBoundPrincipal, Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Override
    public UUID actorId() {
        return null;
    }

    @Override
    public Set<UUID> authorizedCompanyIds() {
        return Set.of();
    }

    @Override
    public Set<String> permissions() {
        return Set.of();
    }

    @Override
    public Map<UUID, Set<String>> permissionsByCompany() {
        return Map.of();
    }
}
