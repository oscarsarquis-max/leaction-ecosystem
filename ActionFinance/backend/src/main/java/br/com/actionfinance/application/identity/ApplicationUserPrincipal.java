package br.com.actionfinance.application.identity;

import java.io.Serial;
import java.io.Serializable;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

public record ApplicationUserPrincipal(
        UUID actorId,
        String displayName,
        Set<UUID> authorizedCompanyIds,
        Set<String> permissions,
        Map<UUID, Set<String>> permissionsByCompany,
        boolean blocked,
        String issuer,
        String subject)
        implements OidcBoundPrincipal, Serializable {

    @Serial
    private static final long serialVersionUID = 2L;
}
