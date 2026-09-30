package br.com.actionfinance.application.identity;

import java.util.Set;

public final class FinancePermissions {

    public static final String SYSTEM_READ = "system:read";
    public static final String COMPANY_CONTEXT_READ = "company-context:read";
    public static final String TITLES_READ = "titles:read";
    public static final String TITLES_WRITE = "titles:write";
    public static final String CATALOGS_READ = "catalogs:read";
    public static final String CATALOGS_WRITE = "catalogs:write";
    public static final String ACCOUNTS_READ = "financial-accounts:read";
    public static final String ACCOUNTS_WRITE = "financial-accounts:write";
    public static final String SETTLEMENTS_READ = "settlements:read";
    public static final String SETTLEMENTS_WRITE = "settlements:write";
    public static final String SETTLEMENTS_REVERSE = "settlements:reverse";

    private static final Set<String> VIEWER = Set.of(
            SYSTEM_READ,
            COMPANY_CONTEXT_READ,
            TITLES_READ,
            CATALOGS_READ,
            ACCOUNTS_READ,
            SETTLEMENTS_READ);

    private static final Set<String> OPERATOR = Set.of(
            SYSTEM_READ,
            COMPANY_CONTEXT_READ,
            TITLES_READ,
            TITLES_WRITE,
            CATALOGS_READ,
            CATALOGS_WRITE,
            ACCOUNTS_READ,
            ACCOUNTS_WRITE,
            SETTLEMENTS_READ,
            SETTLEMENTS_WRITE,
            SETTLEMENTS_REVERSE);

    private FinancePermissions() {}

    public static Set<String> forRole(MembershipRole role) {
        return role == MembershipRole.OPERATOR ? OPERATOR : VIEWER;
    }

    public static Set<String> union(Iterable<MembershipRole> roles) {
        java.util.HashSet<String> permissions = new java.util.HashSet<>();
        for (MembershipRole role : roles) {
            permissions.addAll(forRole(role));
        }
        return Set.copyOf(permissions);
    }
}
