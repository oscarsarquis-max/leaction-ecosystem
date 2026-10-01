package br.com.actionfinance.application.finance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Component
@Profile("local-demo")
public class LocalDemoSeed implements ApplicationRunner {

    public static final LocalDate LOAD_BUSINESS_DATE = LocalDate.of(2026, 9, 15);

    public static final UUID CP_PADARIA_CLIENTE = UUID.fromString("11111111-aaaa-4111-a111-111111111101");
    public static final UUID CP_PADARIA_FORNECEDOR = UUID.fromString("11111111-aaaa-4111-a111-111111111102");
    public static final UUID CP_CLINICA_PACIENTE = UUID.fromString("33333333-aaaa-4333-a333-333333333101");
    public static final UUID CP_CLINICA_LOCADOR = UUID.fromString("33333333-aaaa-4333-a333-333333333102");
    public static final UUID CP_ATELIE_CLIENTE = UUID.fromString("22222222-aaaa-4222-a222-222222222101");
    public static final UUID CAT_VENDA = UUID.fromString("11111111-bbbb-4111-a111-111111111201");
    public static final UUID CAT_ASSINATURA = UUID.fromString("11111111-bbbb-4111-a111-111111111202");
    public static final UUID CAT_INSUMOS = UUID.fromString("11111111-bbbb-4111-a111-111111111203");
    public static final UUID CAT_ALUGUEL = UUID.fromString("11111111-bbbb-4111-a111-111111111204");
    public static final UUID CAT_CONSULTA = UUID.fromString("33333333-bbbb-4333-a333-333333333201");
    public static final UUID CAT_ALUGUEL_C = UUID.fromString("33333333-bbbb-4333-a333-333333333202");
    public static final UUID CAT_VENDA_B = UUID.fromString("22222222-bbbb-4222-a222-222222222201");
    public static final UUID TITLE_REC_SALE = UUID.fromString("11111111-cccc-4111-a111-111111111301");
    public static final UUID TITLE_REC_SUB = UUID.fromString("11111111-cccc-4111-a111-111111111302");
    public static final UUID TITLE_REC_TODAY = UUID.fromString("11111111-cccc-4111-a111-111111111303");
    public static final UUID TITLE_REC_OVERDUE = UUID.fromString("11111111-cccc-4111-a111-111111111304");
    public static final UUID TITLE_REC_DRAFT = UUID.fromString("11111111-cccc-4111-a111-111111111305");
    public static final UUID TITLE_PAG_PURCHASE = UUID.fromString("11111111-cccc-4111-a111-111111111306");
    public static final UUID TITLE_PAG_RENT = UUID.fromString("11111111-cccc-4111-a111-111111111307");
    public static final UUID TITLE_PAG_CANCELLED = UUID.fromString("11111111-cccc-4111-a111-111111111308");
    public static final UUID TITLE_CLINIC_REC = UUID.fromString("33333333-cccc-4333-a333-333333333301");
    public static final UUID TITLE_CLINIC_PAG = UUID.fromString("33333333-cccc-4333-a333-333333333302");
    public static final UUID TITLE_ATELIE_REC = UUID.fromString("22222222-cccc-4222-a222-222222222301");
    public static final UUID TITLE_REC_PARTIAL = UUID.fromString("11111111-cccc-4111-a111-111111111309");
    public static final UUID TITLE_PAG_SETTLED = UUID.fromString("11111111-cccc-4111-a111-111111111310");
    public static final UUID TITLE_REC_REVERSED = UUID.fromString("11111111-cccc-4111-a111-111111111311");
    public static final UUID ACCOUNT_A_BANK = UUID.fromString("11111111-dddd-4111-a111-111111111401");
    public static final UUID ACCOUNT_A_CASH = UUID.fromString("11111111-dddd-4111-a111-111111111402");
    public static final UUID ACCOUNT_B = UUID.fromString("22222222-dddd-4222-a222-222222222401");
    public static final UUID SETTLEMENT_PARTIAL = UUID.fromString("11111111-eeee-4111-a111-111111111501");
    public static final UUID SETTLEMENT_FULL = UUID.fromString("11111111-eeee-4111-a111-111111111502");
    public static final UUID SETTLEMENT_REVERSED = UUID.fromString("11111111-eeee-4111-a111-111111111503");
    public static final UUID REVERSAL_DEMO = UUID.fromString("11111111-ffff-4111-a111-111111111601");

    private final JdbcTemplate jdbc;

    public LocalDemoSeed(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        Instant now = Instant.parse("2026-09-15T12:00:00Z");
        UUID actor = DemoPrincipalCatalog.OPERATOR_A;
        upsertTenant(DemoPrincipalCatalog.TENANT_A, "TENANT-A", "Organização Demonstração A", now);
        upsertTenant(DemoPrincipalCatalog.TENANT_B, "TENANT-B", "Organização Demonstração B", now);
        upsertCompany(
                DemoPrincipalCatalog.COMPANY_A,
                DemoPrincipalCatalog.TENANT_A,
                "PADARIA-EXEMPLO",
                "Padaria Exemplo",
                now);
        upsertCompany(
                DemoPrincipalCatalog.COMPANY_C,
                DemoPrincipalCatalog.TENANT_A,
                "CLINICA-HORIZONTE",
                "Clínica Horizonte",
                now);
        upsertCompany(
                DemoPrincipalCatalog.COMPANY_B,
                DemoPrincipalCatalog.TENANT_B,
                "ATELIE-NORTE",
                "Ateliê Norte",
                now);

        upsertCounterparty(CP_PADARIA_CLIENTE, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, "Cliente Balcão", "CUSTOMER", actor, now);
        upsertCounterparty(CP_PADARIA_FORNECEDOR, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, "Moinho Demonstrativo", "SUPPLIER", actor, now);
        upsertCounterparty(CP_CLINICA_PACIENTE, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_C, "Paciente Demonstrativo", "CUSTOMER", actor, now);
        upsertCounterparty(CP_CLINICA_LOCADOR, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_C, "Imobiliária Demonstrativa", "SUPPLIER", actor, now);
        upsertCounterparty(CP_ATELIE_CLIENTE, DemoPrincipalCatalog.TENANT_B, DemoPrincipalCatalog.COMPANY_B, "Cliente Ateliê", "CUSTOMER", actor, now);

        upsertCategory(CAT_VENDA, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, "Vendas", "RECEIVABLE", actor, now);
        upsertCategory(CAT_ASSINATURA, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, "Parcelas de subscrição", "RECEIVABLE", actor, now);
        upsertCategory(CAT_INSUMOS, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, "Insumos", "PAYABLE", actor, now);
        upsertCategory(CAT_ALUGUEL, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, "Aluguel", "PAYABLE", actor, now);
        upsertCategory(CAT_CONSULTA, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_C, "Consultas", "RECEIVABLE", actor, now);
        upsertCategory(CAT_ALUGUEL_C, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_C, "Aluguel clínico", "PAYABLE", actor, now);
        upsertCategory(CAT_VENDA_B, DemoPrincipalCatalog.TENANT_B, DemoPrincipalCatalog.COMPANY_B, "Encomendas", "RECEIVABLE", actor, now);

        upsertTitle(
                TITLE_REC_SALE,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "RECEIVABLE",
                "OPEN",
                "Venda demonstrativa de pães",
                CP_PADARIA_CLIENTE,
                CAT_VENDA,
                new BigDecimal("12550"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(15),
                "Venda demonstrativa nº 1001",
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_REC_SUB,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "RECEIVABLE",
                "OPEN",
                "Parcela demonstrativa de subscrição",
                CP_PADARIA_CLIENTE,
                CAT_ASSINATURA,
                new BigDecimal("8900"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(35),
                "Parcela demonstrativa 2/12",
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_REC_TODAY,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "RECEIVABLE",
                "OPEN",
                "Recebível com vencimento na data da carga",
                CP_PADARIA_CLIENTE,
                CAT_VENDA,
                new BigDecimal("4500"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE,
                null,
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_REC_OVERDUE,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "RECEIVABLE",
                "OPEN",
                "Recebível vencido na data da carga",
                CP_PADARIA_CLIENTE,
                CAT_VENDA,
                new BigDecimal("3200"),
                LOAD_BUSINESS_DATE.minusDays(10),
                LOAD_BUSINESS_DATE.minusDays(1),
                null,
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_REC_DRAFT,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "RECEIVABLE",
                "DRAFT",
                "Rascunho de recebível demonstrativo",
                null,
                null,
                null,
                null,
                null,
                null,
                actor,
                now,
                null,
                null,
                null);
        upsertTitle(
                TITLE_PAG_PURCHASE,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "PAYABLE",
                "OPEN",
                "Compra demonstrativa de insumos",
                CP_PADARIA_FORNECEDOR,
                CAT_INSUMOS,
                new BigDecimal("18740"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(10),
                "Compra demonstrativa de farinha",
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_PAG_RENT,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "PAYABLE",
                "OPEN",
                "Aluguel demonstrativo do ponto",
                CP_PADARIA_FORNECEDOR,
                CAT_ALUGUEL,
                new BigDecimal("350000"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.minusDays(2),
                "Aluguel setembro demonstrativo",
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_PAG_CANCELLED,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "PAYABLE",
                "CANCELLED",
                "Conta a pagar cancelada na demonstração",
                CP_PADARIA_FORNECEDOR,
                CAT_INSUMOS,
                new BigDecimal("9900"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(7),
                null,
                actor,
                now,
                null,
                now,
                "Cancelada na carga demonstrativa.");
        upsertTitle(
                TITLE_CLINIC_REC,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_C,
                "RECEIVABLE",
                "OPEN",
                "Consulta demonstrativa",
                CP_CLINICA_PACIENTE,
                CAT_CONSULTA,
                new BigDecimal("28000"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(5),
                null,
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_CLINIC_PAG,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_C,
                "PAYABLE",
                "OPEN",
                "Aluguel da clínica demonstrativa",
                CP_CLINICA_LOCADOR,
                CAT_ALUGUEL_C,
                new BigDecimal("420000"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(12),
                null,
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_ATELIE_REC,
                DemoPrincipalCatalog.TENANT_B,
                DemoPrincipalCatalog.COMPANY_B,
                "RECEIVABLE",
                "OPEN",
                "Encomenda demonstrativa do ateliê",
                CP_ATELIE_CLIENTE,
                CAT_VENDA_B,
                new BigDecimal("15000"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(8),
                null,
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_REC_PARTIAL,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "RECEIVABLE",
                "OPEN",
                "Recebível demonstrativo de R$ 150 com baixa parcial",
                CP_PADARIA_CLIENTE,
                CAT_VENDA,
                new BigDecimal("15000"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(20),
                "Jornada PRM_004 recebível 150",
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_PAG_SETTLED,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "PAYABLE",
                "OPEN",
                "Obrigação demonstrativa de R$ 100 quitada",
                CP_PADARIA_FORNECEDOR,
                CAT_INSUMOS,
                new BigDecimal("10000"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(9),
                "Jornada PRM_004 obrigação 100",
                actor,
                now,
                now,
                null,
                null);
        upsertTitle(
                TITLE_REC_REVERSED,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "RECEIVABLE",
                "OPEN",
                "Recebível demonstrativo com baixa estornada",
                CP_PADARIA_CLIENTE,
                CAT_VENDA,
                new BigDecimal("8000"),
                LOAD_BUSINESS_DATE,
                LOAD_BUSINESS_DATE.plusDays(18),
                "Jornada PRM_004 estorno",
                actor,
                now,
                now,
                null,
                null);

        upsertAccount(
                ACCOUNT_A_BANK,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "Conta demonstrativa Banco Exemplo",
                "BANK",
                LOAD_BUSINESS_DATE.minusDays(20),
                new BigDecimal("25000"),
                actor,
                now);
        upsertAccount(
                ACCOUNT_A_CASH,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "Caixa físico demonstrativo",
                "CASH",
                LOAD_BUSINESS_DATE.minusDays(20),
                BigDecimal.ZERO,
                actor,
                now);
        upsertAccount(
                ACCOUNT_B,
                DemoPrincipalCatalog.TENANT_B,
                DemoPrincipalCatalog.COMPANY_B,
                "Conta do ateliê demonstrativo",
                "OTHER",
                LOAD_BUSINESS_DATE.minusDays(10),
                new BigDecimal("5000"),
                actor,
                now);

        upsertSettlementBundle(
                SETTLEMENT_PARTIAL,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                TITLE_REC_PARTIAL,
                ACCOUNT_A_BANK,
                "RECEIVABLE",
                new BigDecimal("5000"),
                LOAD_BUSINESS_DATE.minusDays(2),
                "PIX",
                "Baixa parcial demonstrativa de R$ 50,00",
                actor,
                now,
                2L,
                null,
                null,
                null);
        upsertSettlementBundle(
                SETTLEMENT_FULL,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                TITLE_PAG_SETTLED,
                ACCOUNT_A_BANK,
                "PAYABLE",
                new BigDecimal("10000"),
                LOAD_BUSINESS_DATE.minusDays(1),
                "BANK_TRANSFER",
                "Baixa integral demonstrativa de R$ 100,00",
                actor,
                now,
                2L,
                null,
                null,
                null);
        upsertSettlementBundle(
                SETTLEMENT_REVERSED,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                TITLE_REC_REVERSED,
                ACCOUNT_A_CASH,
                "RECEIVABLE",
                new BigDecimal("3000"),
                LOAD_BUSINESS_DATE.minusDays(3),
                "CASH",
                "Baixa depois estornada na demonstração",
                actor,
                now,
                3L,
                REVERSAL_DEMO,
                LOAD_BUSINESS_DATE.minusDays(1),
                "Estorno demonstrativo de registro indevido");
        upsertPayMapping(
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "homolog-padaria",
                now);
    }

    private void upsertPayMapping(UUID tenantId, UUID companyId, String payAppId, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.pay_company_mapping (
                    id, tenant_id, company_id, pay_app_id, environment, authorized, created_at, updated_at)
                values (?,?,?,?, 'HOMOLOG', true, ?, ?)
                on conflict (tenant_id, company_id) do nothing
                """,
                UUID.fromString("11111111-aaaa-4111-a111-111111111801"),
                tenantId,
                companyId,
                payAppId,
                Timestamp.from(now),
                Timestamp.from(now));
    }

    private void upsertTenant(UUID id, String code, String name, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.tenant (id, code, name, active, created_at, updated_at, version)
                values (?,?,?,true,?,?,1)
                on conflict (id) do nothing
                """,
                id,
                code,
                name,
                Timestamp.from(now),
                Timestamp.from(now));
    }

    private void upsertCompany(UUID id, UUID tenantId, String code, String name, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.company (
                    id, tenant_id, code, name, active, is_demo, business_timezone, created_at, updated_at, version)
                values (?,?,?,?,true,true,'America/Sao_Paulo',?,?,1)
                on conflict (id) do nothing
                """,
                id,
                tenantId,
                code,
                name,
                Timestamp.from(now),
                Timestamp.from(now));
    }

    private void upsertCounterparty(
            UUID id, UUID tenantId, UUID companyId, String name, String role, UUID actor, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.counterparty (
                    id, tenant_id, company_id, code, name, role, active, version,
                    created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,?,true,1,?,?,?,?)
                on conflict (id) do nothing
                """,
                id,
                tenantId,
                companyId,
                "CTP-" + id,
                name,
                role,
                Timestamp.from(now),
                Timestamp.from(now),
                actor,
                actor);
    }

    private void upsertCategory(
            UUID id, UUID tenantId, UUID companyId, String name, String direction, UUID actor, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.financial_category (
                    id, tenant_id, company_id, code, name, direction, active, version,
                    created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,?,true,1,?,?,?,?)
                on conflict (id) do nothing
                """,
                id,
                tenantId,
                companyId,
                "CAT-" + id,
                name,
                direction,
                Timestamp.from(now),
                Timestamp.from(now),
                actor,
                actor);
    }

    private void upsertTitle(
            UUID id,
            UUID tenantId,
            UUID companyId,
            String direction,
            String status,
            String description,
            UUID counterpartyId,
            UUID categoryId,
            BigDecimal amount,
            LocalDate competence,
            LocalDate due,
            String sourceReference,
            UUID actor,
            Instant now,
            Instant confirmedAt,
            Instant cancelledAt,
            String cancelReason) {
        String prefix = "RECEIVABLE".equals(direction) ? "REC-" : "PAG-";
        jdbc.update(
                """
                insert into actionfinance.financial_title (
                    id, tenant_id, company_id, reference, direction, status, description,
                    counterparty_id, category_id, amount_minor, currency, competence_date, due_date,
                    origin_kind, source_reference, version, created_at, updated_at, created_by, updated_by,
                    confirmed_at, cancelled_at, cancellation_reason)
                values (?,?,?,?,?,?,?,?,?,?,'BRL',?,?,'MANUAL',?,1,?,?,?,?,?,?,?)
                on conflict (id) do nothing
                """,
                id,
                tenantId,
                companyId,
                prefix + id,
                direction,
                status,
                description,
                counterpartyId,
                categoryId,
                amount,
                competence == null ? null : Date.valueOf(competence),
                due == null ? null : Date.valueOf(due),
                sourceReference,
                Timestamp.from(now),
                Timestamp.from(now),
                actor,
                actor,
                confirmedAt == null ? null : Timestamp.from(confirmedAt),
                cancelledAt == null ? null : Timestamp.from(cancelledAt),
                cancelReason);
        jdbc.update(
                """
                insert into actionfinance.financial_title_history (
                    id, tenant_id, company_id, title_id, title_version, action,
                    actor_id, actor_display_name, occurred_at, reason, changes)
                select ?, ?, ?, ?, 1, ?, ?, 'Carga demonstrativa', ?, ?, '{}'::jsonb
                where not exists (
                    select 1 from actionfinance.financial_title_history
                    where tenant_id = ? and company_id = ? and title_id = ? and title_version = 1)
                """,
                UUID.randomUUID(),
                tenantId,
                companyId,
                id,
                "CANCELLED".equals(status) ? "CANCELLED" : "CREATED",
                actor,
                Timestamp.from(now),
                cancelReason,
                tenantId,
                companyId,
                id);
    }

    private void upsertAccount(
            UUID id,
            UUID tenantId,
            UUID companyId,
            String name,
            String type,
            LocalDate openedOn,
            BigDecimal opening,
            UUID actor,
            Instant now) {
        jdbc.update(
                """
                insert into actionfinance.financial_account (
                    id, tenant_id, company_id, code, name, type, currency, active, opened_on,
                    version, created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,?,'BRL',true,?,1,?,?,?,?)
                on conflict (id) do nothing
                """,
                id,
                tenantId,
                companyId,
                "CTA-" + id,
                name,
                type,
                Date.valueOf(openedOn),
                Timestamp.from(now),
                Timestamp.from(now),
                actor,
                actor);
        jdbc.update(
                """
                insert into actionfinance.cash_movement (
                    id, tenant_id, company_id, account_id, kind, signed_amount_minor, currency,
                    effective_date, recorded_at, recorded_by, settlement_id, reversal_id, description)
                select ?, ?, ?, ?, 'OPENING', ?, 'BRL', ?, ?, ?, null, null, 'Saldo inicial informado'
                where not exists (
                    select 1 from actionfinance.cash_movement
                    where tenant_id = ? and company_id = ? and account_id = ? and kind = 'OPENING')
                """,
                UUID.nameUUIDFromBytes(("open-" + id).getBytes()),
                tenantId,
                companyId,
                id,
                opening,
                Date.valueOf(openedOn),
                Timestamp.from(now),
                actor,
                tenantId,
                companyId,
                id);
        jdbc.update(
                """
                insert into actionfinance.financial_account_history (
                    id, tenant_id, company_id, account_id, account_version, action, actor_id, occurred_at, changes)
                select ?, ?, ?, ?, 1, 'CREATED', ?, ?, '{"source":"seed"}'::jsonb
                where not exists (
                    select 1 from actionfinance.financial_account_history
                    where tenant_id = ? and company_id = ? and account_id = ? and account_version = 1)
                """,
                UUID.nameUUIDFromBytes(("ah-" + id).getBytes()),
                tenantId,
                companyId,
                id,
                actor,
                Timestamp.from(now),
                tenantId,
                companyId,
                id);
    }

    private void upsertSettlementBundle(
            UUID settlementId,
            UUID tenantId,
            UUID companyId,
            UUID titleId,
            UUID accountId,
            String direction,
            BigDecimal amount,
            LocalDate effective,
            String method,
            String note,
            UUID actor,
            Instant now,
            long titleVersionAfter,
            UUID reversalId,
            LocalDate reversalDate,
            String reversalReason) {
        BigDecimal signed = "RECEIVABLE".equals(direction) ? amount : amount.negate();
        jdbc.update(
                """
                insert into actionfinance.settlement (
                    id, tenant_id, company_id, account_id, direction, amount_minor, currency,
                    effective_date, method, note, origin_kind, recorded_at, recorded_by, actor_display_name)
                values (?,?,?,?,?,?,'BRL',?,?,?,'MANUAL',?,?,?)
                on conflict (id) do nothing
                """,
                settlementId,
                tenantId,
                companyId,
                accountId,
                direction,
                amount,
                Date.valueOf(effective),
                method,
                note,
                Timestamp.from(now),
                actor,
                "Carga demonstrativa");
        jdbc.update(
                """
                insert into actionfinance.settlement_allocation (
                    id, tenant_id, company_id, settlement_id, title_id, amount_minor)
                values (?,?,?,?,?,?)
                on conflict (id) do nothing
                """,
                UUID.nameUUIDFromBytes(("alloc-" + settlementId).getBytes()),
                tenantId,
                companyId,
                settlementId,
                titleId,
                amount);
        jdbc.update(
                """
                insert into actionfinance.cash_movement (
                    id, tenant_id, company_id, account_id, kind, signed_amount_minor, currency,
                    effective_date, recorded_at, recorded_by, settlement_id, reversal_id, description)
                select ?, ?, ?, ?, 'SETTLEMENT', ?, 'BRL', ?, ?, ?, ?, null, ?
                where not exists (
                    select 1 from actionfinance.cash_movement
                    where tenant_id = ? and company_id = ? and settlement_id = ? and kind = 'SETTLEMENT')
                """,
                UUID.nameUUIDFromBytes(("mov-" + settlementId).getBytes()),
                tenantId,
                companyId,
                accountId,
                signed,
                Date.valueOf(effective),
                Timestamp.from(now),
                actor,
                settlementId,
                "RECEIVABLE".equals(direction) ? "Recebimento registrado · seed" : "Pagamento registrado · seed",
                tenantId,
                companyId,
                settlementId);
        if (reversalId != null) {
            jdbc.update(
                    """
                    insert into actionfinance.settlement_reversal (
                        id, tenant_id, company_id, settlement_id, effective_date, reason,
                        recorded_at, recorded_by, actor_display_name)
                    values (?,?,?,?,?,?,?,?,?)
                    on conflict (id) do nothing
                    """,
                    reversalId,
                    tenantId,
                    companyId,
                    settlementId,
                    Date.valueOf(reversalDate),
                    reversalReason,
                    Timestamp.from(now),
                    actor,
                    "Carga demonstrativa");
            jdbc.update(
                    """
                    insert into actionfinance.cash_movement (
                        id, tenant_id, company_id, account_id, kind, signed_amount_minor, currency,
                        effective_date, recorded_at, recorded_by, settlement_id, reversal_id, description)
                    select ?, ?, ?, ?, 'REVERSAL', ?, 'BRL', ?, ?, ?, ?, ?, 'Estorno do registro · seed'
                    where not exists (
                        select 1 from actionfinance.cash_movement
                        where tenant_id = ? and company_id = ? and reversal_id = ? and kind = 'REVERSAL')
                    """,
                    UUID.nameUUIDFromBytes(("revmov-" + reversalId).getBytes()),
                    tenantId,
                    companyId,
                    accountId,
                    signed.negate(),
                    Date.valueOf(reversalDate),
                    Timestamp.from(now),
                    actor,
                    settlementId,
                    reversalId,
                    tenantId,
                    companyId,
                    reversalId);
        }
        jdbc.update(
                """
                update actionfinance.financial_title
                set version = ?, updated_at = ?
                where tenant_id = ? and company_id = ? and id = ? and version < ?
                """,
                titleVersionAfter,
                Timestamp.from(now),
                tenantId,
                companyId,
                titleId,
                titleVersionAfter);
        jdbc.update(
                """
                insert into actionfinance.financial_title_history (
                    id, tenant_id, company_id, title_id, title_version, action,
                    actor_id, actor_display_name, occurred_at, reason, changes)
                select ?, ?, ?, ?, 2, 'SETTLEMENT_RECORDED', ?, 'Carga demonstrativa', ?, ?, '{}'::jsonb
                where not exists (
                    select 1 from actionfinance.financial_title_history
                    where tenant_id = ? and company_id = ? and title_id = ? and title_version = 2)
                """,
                UUID.nameUUIDFromBytes(("th2-" + settlementId).getBytes()),
                tenantId,
                companyId,
                titleId,
                actor,
                Timestamp.from(now),
                note,
                tenantId,
                companyId,
                titleId);
        if (reversalId != null) {
            jdbc.update(
                    """
                    insert into actionfinance.financial_title_history (
                        id, tenant_id, company_id, title_id, title_version, action,
                        actor_id, actor_display_name, occurred_at, reason, changes)
                    select ?, ?, ?, ?, 3, 'SETTLEMENT_REVERSED', ?, 'Carga demonstrativa', ?, ?, '{}'::jsonb
                    where not exists (
                        select 1 from actionfinance.financial_title_history
                        where tenant_id = ? and company_id = ? and title_id = ? and title_version = 3)
                    """,
                    UUID.nameUUIDFromBytes(("th3-" + reversalId).getBytes()),
                    tenantId,
                    companyId,
                    titleId,
                    actor,
                    Timestamp.from(now),
                    reversalReason,
                    tenantId,
                    companyId,
                    titleId);
        }
    }
}
