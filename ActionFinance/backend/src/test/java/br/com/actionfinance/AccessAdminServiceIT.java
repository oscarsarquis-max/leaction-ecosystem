package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.identity.AccessAdminService;
import br.com.actionfinance.application.identity.IdentityAuthorizationService;
import br.com.actionfinance.application.identity.MembershipRole;
import br.com.actionfinance.support.AccessTestData;
import br.com.actionfinance.support.PostgresFoundationContainer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@Testcontainers
class AccessAdminServiceIT {

    @Container
    static final PostgreSQLContainer<?> POSTGRES = PostgresFoundationContainer.create();

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "actionfinance_runtime");
        registry.add("spring.datasource.password", () -> "runtime-test");
        registry.add("spring.flyway.user", () -> "actionfinance_migrator");
        registry.add("spring.flyway.password", () -> "migrator-test");
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("actionfinance.demo-auth.enabled", () -> "false");
    }

    @Autowired
    AccessAdminService admin;

    @Autowired
    IdentityAuthorizationService identities;

    @Autowired
    JdbcTemplate jdbc;

    @BeforeEach
    void companies() {
        AccessTestData.seedCompanies(jdbc);
    }

    @Test
    void provisionIsIdempotentAndDoesNotGrantByEmail() {
        AccessAdminService.Result dry =
                admin.provision(
                        "Operadora",
                        "https://idp.example/realms/af",
                        "sub-operator",
                        DemoPrincipalCatalog.TENANT_A,
                        DemoPrincipalCatalog.COMPANY_A,
                        MembershipRole.OPERATOR,
                        "Liberação inicial do ciclo",
                        "test",
                        "corr-admin-1",
                        true);
        assertThat(dry.changed()).isTrue();
        assertThat(jdbc.queryForObject("select count(*) from actionfinance.app_user", Integer.class)).isZero();

        AccessAdminService.Result first =
                admin.provision(
                        "Operadora",
                        "https://idp.example/realms/af",
                        "sub-operator",
                        DemoPrincipalCatalog.TENANT_A,
                        DemoPrincipalCatalog.COMPANY_A,
                        MembershipRole.OPERATOR,
                        "Liberação inicial do ciclo",
                        "test",
                        "corr-admin-1",
                        false);
        AccessAdminService.Result second =
                admin.provision(
                        "Operadora",
                        "https://idp.example/realms/af",
                        "sub-operator",
                        DemoPrincipalCatalog.TENANT_A,
                        DemoPrincipalCatalog.COMPANY_A,
                        MembershipRole.OPERATOR,
                        "Repetição sem duplicar",
                        "test",
                        "corr-admin-2",
                        false);
        assertThat(first.changed()).isTrue();
        assertThat(second.changed()).isFalse();
        assertThat(second.userId()).isEqualTo(first.userId());
        assertThat(jdbc.queryForObject("select count(*) from actionfinance.app_user", Integer.class)).isEqualTo(1);

        admin.provision(
                "Outra pessoa",
                "https://idp.example/realms/af",
                "sub-other",
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_C,
                MembershipRole.VIEWER,
                "Segundo subject, mesmo email no provedor",
                "test",
                null,
                false);
        var sameEmailOtherSubject =
                identities.resolve("https://idp.example/realms/af", "sub-other", "mesmo.email@example");
        assertThat(sameEmailOtherSubject.authorizedCompanyIds()).containsExactly(DemoPrincipalCatalog.COMPANY_C);
        assertThat(sameEmailOtherSubject.canAccess(DemoPrincipalCatalog.COMPANY_A)).isFalse();
    }

    @Test
    void blockAndRevokeTakeEffectOnNextResolve() {
        AccessAdminService.Result created =
                admin.provision(
                        "Consulta",
                        "https://idp.example/realms/af",
                        "sub-viewer",
                        DemoPrincipalCatalog.TENANT_A,
                        DemoPrincipalCatalog.COMPANY_A,
                        MembershipRole.VIEWER,
                        "Acesso temporário",
                        "test",
                        null,
                        false);
        UUID userId = created.userId();
        assertThat(identities.resolve("https://idp.example/realms/af", "sub-viewer", "Consulta").accessState().name())
                .isEqualTo("READY");

        admin.revoke(
                userId,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "Fim do contrato",
                "test",
                false);
        assertThat(identities.resolve("https://idp.example/realms/af", "sub-viewer", "Consulta").accessState().name())
                .isEqualTo("NO_COMPANY");

        admin.provision(
                "Consulta",
                "https://idp.example/realms/af",
                "sub-viewer",
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                MembershipRole.VIEWER,
                "Reativar",
                "test",
                null,
                false);
        admin.setBlocked(userId, true, "Uso indevido", "test", false);
        assertThat(identities.resolve("https://idp.example/realms/af", "sub-viewer", "Consulta").blocked()).isTrue();
        assertThatThrownBy(
                        () ->
                                admin.provision(
                                        "X",
                                        "https://idp.example/realms/af",
                                        "sub-viewer",
                                        UUID.randomUUID(),
                                        DemoPrincipalCatalog.COMPANY_A,
                                        MembershipRole.OPERATOR,
                                        "empresa inválida",
                                        "test",
                                        null,
                                        false))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void bootstrapOrganizationIsTransactionalAndHonorsDryRun() {
        AccessAdminService.Result dry =
                admin.bootstrapOrganization(
                        "TENANT-ENSAIO",
                        "Organização Ensaio",
                        "EMP-ENSAIO",
                        "Empresa Ensaio",
                        "America/Sao_Paulo",
                        "Responsável do ensaio",
                        "Criação inicial descartável",
                        "test",
                        true);
        assertThat(dry.changed()).isTrue();
        assertThat(dry.summary()).contains("DRY-RUN");
        assertThat(
                        jdbc.queryForObject(
                                "select count(*) from actionfinance.tenant where code = 'TENANT-ENSAIO'",
                                Integer.class))
                .isZero();

        AccessAdminService.Result created =
                admin.bootstrapOrganization(
                        "TENANT-ENSAIO",
                        "Organização Ensaio",
                        "EMP-ENSAIO",
                        "Empresa Ensaio",
                        "America/Sao_Paulo",
                        "Responsável do ensaio",
                        "Criação inicial descartável",
                        "test",
                        false);
        assertThat(created.changed()).isTrue();
        assertThat(
                        jdbc.queryForObject(
                                "select count(*) from actionfinance.company where code = 'EMP-ENSAIO'",
                                Integer.class))
                .isEqualTo(1);
        assertThatThrownBy(
                        () ->
                                admin.bootstrapOrganization(
                                        "TENANT-ENSAIO",
                                        "Organização Ensaio",
                                        "EMP-ENSAIO-2",
                                        "Outra",
                                        "America/Sao_Paulo",
                                        "Responsável",
                                        "Duplicar código",
                                        "test",
                                        false))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Tenant code");
    }
}
