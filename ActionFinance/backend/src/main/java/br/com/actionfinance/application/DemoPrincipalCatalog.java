package br.com.actionfinance.application;

import br.com.actionfinance.application.identity.FinancePermissions;

import java.util.Set;
import java.util.UUID;

public final class DemoPrincipalCatalog {

    public static final UUID COMPANY_A = UUID.fromString("11111111-1111-4111-a111-111111111111");
    public static final UUID COMPANY_B = UUID.fromString("22222222-2222-4222-a222-222222222222");
    public static final UUID COMPANY_C = UUID.fromString("33333333-3333-4333-a333-333333333333");
    public static final UUID TENANT_A = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0001");
    public static final UUID TENANT_B = UUID.fromString("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbb0001");
    public static final UUID OPERATOR_A = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1");
    public static final UUID VIEWER_A = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2");
    public static final UUID VIEWER_B = UUID.fromString("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2");
    public static final UUID OPERATOR_MULTI = UUID.fromString("cccccccc-cccc-4ccc-8ccc-ccccccccccc1");
    public static final UUID MIXED_AB = UUID.fromString("dddddddd-dddd-4ddd-8ddd-ddddddddddd1");

    public static final String PERMISSION_SYSTEM_READ = FinancePermissions.SYSTEM_READ;
    public static final String PERMISSION_COMPANY_CONTEXT_READ = FinancePermissions.COMPANY_CONTEXT_READ;
    public static final String PERMISSION_TITLES_READ = FinancePermissions.TITLES_READ;
    public static final String PERMISSION_TITLES_WRITE = FinancePermissions.TITLES_WRITE;
    public static final String PERMISSION_CATALOGS_READ = FinancePermissions.CATALOGS_READ;
    public static final String PERMISSION_CATALOGS_WRITE = FinancePermissions.CATALOGS_WRITE;
    public static final String PERMISSION_ACCOUNTS_READ = FinancePermissions.ACCOUNTS_READ;
    public static final String PERMISSION_ACCOUNTS_WRITE = FinancePermissions.ACCOUNTS_WRITE;
    public static final String PERMISSION_SETTLEMENTS_READ = FinancePermissions.SETTLEMENTS_READ;
    public static final String PERMISSION_SETTLEMENTS_WRITE = FinancePermissions.SETTLEMENTS_WRITE;
    public static final String PERMISSION_SETTLEMENTS_REVERSE = FinancePermissions.SETTLEMENTS_REVERSE;

    private static final Set<String> READ = Set.of(
            PERMISSION_SYSTEM_READ,
            PERMISSION_COMPANY_CONTEXT_READ,
            PERMISSION_TITLES_READ,
            PERMISSION_CATALOGS_READ,
            PERMISSION_ACCOUNTS_READ,
            PERMISSION_SETTLEMENTS_READ);

    private static final Set<String> WRITE = Set.of(
            PERMISSION_SYSTEM_READ,
            PERMISSION_COMPANY_CONTEXT_READ,
            PERMISSION_TITLES_READ,
            PERMISSION_TITLES_WRITE,
            PERMISSION_CATALOGS_READ,
            PERMISSION_CATALOGS_WRITE,
            PERMISSION_ACCOUNTS_READ,
            PERMISSION_ACCOUNTS_WRITE,
            PERMISSION_SETTLEMENTS_READ,
            PERMISSION_SETTLEMENTS_WRITE,
            PERMISSION_SETTLEMENTS_REVERSE);

    public static final DemoPrincipal OPERATOR_COMPANY_A = new DemoPrincipal(
            OPERATOR_A, "Operador empresa A", Set.of(COMPANY_A), WRITE);

    public static final DemoPrincipal VIEWER_COMPANY_A = new DemoPrincipal(
            VIEWER_A, "Consulta empresa A", Set.of(COMPANY_A), READ);

    public static final DemoPrincipal VIEWER_COMPANY_B = new DemoPrincipal(
            VIEWER_B, "Consulta empresa B", Set.of(COMPANY_B), READ);

    public static final DemoPrincipal OPERATOR_MULTI_AC = new DemoPrincipal(
            OPERATOR_MULTI, "Operador duas empresas (fixture)", Set.of(COMPANY_A, COMPANY_C), WRITE);

    public static final DemoPrincipal MIXED_A_OPERATOR_B_VIEWER =
            new DemoPrincipal(
                    MIXED_AB,
                    "Operador A e consulta B (fixture)",
                    Set.of(COMPANY_A, COMPANY_B),
                    FinancePermissions.union(
                            java.util.List.of(
                                    br.com.actionfinance.application.identity.MembershipRole.OPERATOR,
                                    br.com.actionfinance.application.identity.MembershipRole.VIEWER)),
                    java.util.Map.of(COMPANY_A, WRITE, COMPANY_B, READ));

    private DemoPrincipalCatalog() {}
}
