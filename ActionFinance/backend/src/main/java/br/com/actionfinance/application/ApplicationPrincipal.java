package br.com.actionfinance.application;

import br.com.actionfinance.application.identity.AccessState;
import org.springframework.security.core.AuthenticatedPrincipal;

import java.util.Map;
import java.util.Set;
import java.util.UUID;

public interface ApplicationPrincipal extends AuthenticatedPrincipal {

    UUID actorId();

    String displayName();

    Set<UUID> authorizedCompanyIds();

    /**
     * Union of permissions across companies. Used only for HTTP navigation
     * (can the actor reach a write route at all). Financial writes must use
     * {@link #permissionsFor(UUID)} on the resource company.
     */
    Set<String> permissions();

    Map<UUID, Set<String>> permissionsByCompany();

    default Set<String> permissionsFor(UUID companyId) {
        if (companyId == null) {
            return Set.of();
        }
        Set<String> granted = permissionsByCompany().get(companyId);
        return granted == null ? Set.of() : granted;
    }

    default boolean hasPermission(UUID companyId, String permission) {
        return permission != null && permissionsFor(companyId).contains(permission);
    }

    default boolean canAccess(UUID companyId) {
        return companyId != null && authorizedCompanyIds().contains(companyId);
    }

    default boolean blocked() {
        return false;
    }

    @Override
    default String getName() {
        return actorId() != null ? actorId().toString() : "unprovisioned";
    }

    default AccessState accessState() {
        if (blocked()) {
            return AccessState.BLOCKED;
        }
        if (actorId() == null) {
            return AccessState.NOT_PROVISIONED;
        }
        if (authorizedCompanyIds().isEmpty()) {
            return AccessState.NO_COMPANY;
        }
        return AccessState.READY;
    }
}
