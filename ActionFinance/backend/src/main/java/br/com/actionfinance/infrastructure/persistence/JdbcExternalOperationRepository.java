package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.integration.ExternalLookupView;
import br.com.actionfinance.application.integration.LookupAttemptStart;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcExternalOperationRepository {

    private final JdbcTemplate jdbc;

    public JdbcExternalOperationRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public boolean mappingAuthorized(AuthorizedScope scope) {
        Integer count =
                jdbc.queryForObject(
                        """
                        select count(*) from actionfinance.pay_company_mapping
                        where tenant_id = ? and company_id = ? and authorized = true
                        """,
                        Integer.class,
                        scope.tenantId(),
                        scope.companyId());
        return count != null && count > 0;
    }

    public Optional<ExternalLookupView> findByTitle(AuthorizedScope scope, UUID titleId) {
        return first(
                """
                select * from actionfinance.external_operation
                where tenant_id = ? and company_id = ? and title_id = ?
                order by updated_at desc
                limit 1
                """,
                scope.tenantId(),
                scope.companyId(),
                titleId);
    }

    public Optional<ExternalLookupView> findByReference(AuthorizedScope scope, String externalReference) {
        return first(
                """
                select * from actionfinance.external_operation
                where tenant_id = ? and company_id = ? and origin_system = 'ACTIONHUB_PAY' and external_reference = ?
                """,
                scope.tenantId(),
                scope.companyId(),
                externalReference);
    }

    public Optional<ExternalLookupView> findById(AuthorizedScope scope, UUID id) {
        return first(
                """
                select * from actionfinance.external_operation
                where tenant_id = ? and company_id = ? and id = ?
                """,
                scope.tenantId(),
                scope.companyId(),
                id);
    }

    public ExternalLookupView insertOrGet(AuthorizedScope scope, ExternalLookupView view, String fingerprint) {
        try {
            jdbc.update(
                    """
                    insert into actionfinance.external_operation (
                        id, tenant_id, company_id, title_id, capability, origin_system, origin_kind,
                        external_reference, amount_minor, currency, external_status, delivery_status,
                        idempotency_key, semantic_fingerprint, correlation_id, spider_decision_id,
                        provider_reference, provider_origin, last_error, observed_at, created_at, updated_at,
                        last_attempt_outcome, last_attempt_at, last_attempt_id, version)
                    values (?,?,?,?, 'LOOKUP_ACTIONHUB_PAYMENT', 'ACTIONHUB_PAY', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    view.id(),
                    scope.tenantId(),
                    scope.companyId(),
                    view.titleId(),
                    view.titleId() == null ? "STANDALONE" : "TITLE",
                    view.externalReference(),
                    view.amountMinor(),
                    view.currency(),
                    view.externalStatus(),
                    view.deliveryStatus(),
                    "lookup:" + view.companyId() + ":" + view.externalReference(),
                    fingerprint,
                    view.correlationId(),
                    view.spiderDecisionId(),
                    view.providerReference(),
                    view.providerOrigin(),
                    view.lastError(),
                    timestamp(view.observedAt()),
                    timestamp(view.updatedAt()),
                    timestamp(view.updatedAt()),
                    view.lastAttemptOutcome(),
                    timestamp(view.lastAttemptAt()),
                    view.lastAttemptId());
            return view;
        } catch (DataIntegrityViolationException ignored) {
            return findByReference(scope, view.externalReference()).orElseThrow();
        }
    }

    public ExternalLookupView lockOperation(AuthorizedScope scope, UUID operationId) {
        return first(
                        """
                        select * from actionfinance.external_operation
                        where tenant_id = ? and company_id = ? and id = ?
                        for update
                        """,
                        scope.tenantId(),
                        scope.companyId(),
                        operationId)
                .orElseThrow();
    }

    public boolean attemptStillOpen(AuthorizedScope scope, UUID attemptId) {
        Boolean open =
                jdbc.query(
                                """
                                select completed_at is null as open
                                from actionfinance.lookup_attempt
                                where tenant_id = ? and company_id = ? and id = ?
                                for update
                                """,
                                (rs, rowNum) -> rs.getBoolean("open"),
                                scope.tenantId(),
                                scope.companyId(),
                                attemptId)
                        .stream()
                        .findFirst()
                        .orElse(false);
        return Boolean.TRUE.equals(open);
    }

    public LookupAttemptStart beginAttempt(AuthorizedScope scope, ExternalLookupView operation, Instant started) {
        lockOperation(scope, operation.id());
        UUID attemptId = UUID.randomUUID();
        String hop = "afa-" + attemptId;
        jdbc.update(
                """
                insert into actionfinance.lookup_attempt (
                    id, tenant_id, company_id, operation_id, correlation_id, outcome, created_at,
                    started_at, completed_at, received_outcome, observation_applied, discarded_reason,
                    attempt_correlation_id)
                values (?,?,?,?,?, 'STARTED', ?, ?, null, null, false, null, ?)
                """,
                attemptId,
                scope.tenantId(),
                scope.companyId(),
                operation.id(),
                hop,
                timestamp(started),
                timestamp(started),
                hop);
        jdbc.update(
                """
                update actionfinance.external_operation
                set last_attempt_outcome = 'STARTED', last_attempt_at = ?, last_attempt_id = ?, updated_at = ?
                where tenant_id = ? and company_id = ? and id = ?
                  and (last_attempt_at is null or last_attempt_at <= ?)
                """,
                timestamp(started),
                attemptId,
                timestamp(started),
                scope.tenantId(),
                scope.companyId(),
                operation.id(),
                timestamp(started));
        return new LookupAttemptStart(attemptId, hop, operation, started);
    }

    public boolean finishAttempt(
            AuthorizedScope scope,
            UUID attemptId,
            String receivedOutcome,
            boolean observationApplied,
            String discardedReason,
            Instant completedAt) {
        int updated =
                jdbc.update(
                        """
                        update actionfinance.lookup_attempt
                        set outcome = ?, completed_at = ?, received_outcome = ?,
                            observation_applied = ?, discarded_reason = ?
                        where tenant_id = ? and company_id = ? and id = ? and completed_at is null
                        """,
                        receivedOutcome,
                        timestamp(completedAt),
                        receivedOutcome,
                        observationApplied,
                        discardedReason,
                        scope.tenantId(),
                        scope.companyId(),
                        attemptId);
        return updated == 1;
    }

    public int markRecoveredIfCurrentAttempt(
            AuthorizedScope scope, UUID operationId, UUID attemptId, Instant notAfter, Instant at) {
        return jdbc.update(
                """
                update actionfinance.external_operation
                set last_attempt_outcome = 'UNAVAILABLE',
                    last_attempt_at = ?,
                    delivery_status = 'UNAVAILABLE',
                    last_error = ?,
                    updated_at = ?
                where tenant_id = ? and company_id = ? and id = ?
                  and last_attempt_id = ?
                  and last_attempt_outcome = 'STARTED'
                  and last_attempt_at <= ?
                """,
                timestamp(at),
                "Não foi possível atualizar. A observação anterior foi preservada.",
                timestamp(at),
                scope.tenantId(),
                scope.companyId(),
                operationId,
                attemptId,
                timestamp(notAfter));
    }

    public java.util.List<UUID> openAttemptIds(AuthorizedScope scope, UUID operationId, Instant olderThan) {
        return jdbc.query(
                """
                select id from actionfinance.lookup_attempt
                where tenant_id = ? and company_id = ? and operation_id = ?
                  and completed_at is null and outcome = 'STARTED' and started_at <= ?
                """,
                (rs, rowNum) -> rs.getObject("id", UUID.class),
                scope.tenantId(),
                scope.companyId(),
                operationId,
                timestamp(olderThan));
    }

    public void setMappingAuthorized(AuthorizedScope scope, boolean authorized) {
        jdbc.update(
                """
                update actionfinance.pay_company_mapping
                set authorized = ?, updated_at = now()
                where tenant_id = ? and company_id = ?
                """,
                authorized,
                scope.tenantId(),
                scope.companyId());
    }

    public void upgradeFingerprint(AuthorizedScope scope, UUID id, String fingerprint) {
        jdbc.update(
                """
                update actionfinance.external_operation
                set semantic_fingerprint = ?
                where tenant_id = ? and company_id = ? and id = ?
                """,
                fingerprint,
                scope.tenantId(),
                scope.companyId(),
                id);
    }

    public boolean updateIfVersion(AuthorizedScope scope, ExternalLookupView view) {
        int updated =
                jdbc.update(
                        """
                        update actionfinance.external_operation
                        set external_status = ?, delivery_status = ?, amount_minor = ?, currency = ?,
                            spider_decision_id = ?, provider_reference = ?, provider_origin = ?,
                            last_error = ?, observed_at = ?, updated_at = ?,
                            last_attempt_outcome = ?, last_attempt_at = ?, last_attempt_id = ?,
                            version = version + 1
                        where tenant_id = ? and company_id = ? and id = ? and version = ?
                          and (last_attempt_at is null or last_attempt_at <= ?)
                        """,
                        view.externalStatus(),
                        view.deliveryStatus(),
                        view.amountMinor(),
                        view.currency(),
                        view.spiderDecisionId(),
                        view.providerReference(),
                        view.providerOrigin(),
                        view.lastError(),
                        timestamp(view.observedAt()),
                        timestamp(view.updatedAt()),
                        view.lastAttemptOutcome(),
                        timestamp(view.lastAttemptAt()),
                        view.lastAttemptId(),
                        scope.tenantId(),
                        scope.companyId(),
                        view.id(),
                        view.version(),
                        timestamp(view.lastAttemptAt()));
        return updated == 1;
    }

    public void insertAttempt(
            AuthorizedScope scope, UUID operationId, UUID attemptId, String correlationId, String outcome, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.lookup_attempt (
                    id, tenant_id, company_id, operation_id, correlation_id, outcome, created_at)
                values (?,?,?,?,?,?,?)
                """,
                attemptId,
                scope.tenantId(),
                scope.companyId(),
                operationId,
                correlationId,
                outcome,
                timestamp(now));
    }

    public Optional<String> fingerprint(AuthorizedScope scope, String externalReference) {
        List<String> rows =
                jdbc.query(
                        """
                        select semantic_fingerprint from actionfinance.external_operation
                        where tenant_id = ? and company_id = ? and origin_system = 'ACTIONHUB_PAY'
                          and external_reference = ?
                        """,
                        (rs, rowNum) -> rs.getString("semantic_fingerprint"),
                        scope.tenantId(),
                        scope.companyId(),
                        externalReference);
        return rows.stream().findFirst();
    }

    private Optional<ExternalLookupView> first(String sql, Object... args) {
        List<ExternalLookupView> rows = jdbc.query(sql, (rs, rowNum) -> map(rs), args);
        return rows.stream().findFirst();
    }

    private static Timestamp timestamp(Instant value) {
        return value == null ? null : Timestamp.from(value);
    }

    private ExternalLookupView map(java.sql.ResultSet rs) throws java.sql.SQLException {
        Timestamp observed = rs.getTimestamp("observed_at");
        Timestamp updated = rs.getTimestamp("updated_at");
        Timestamp attempted = column(rs, "last_attempt_at");
        BigDecimal amount = rs.getBigDecimal("amount_minor");
        return new ExternalLookupView(
                rs.getObject("id", UUID.class),
                rs.getObject("company_id", UUID.class),
                rs.getObject("title_id", UUID.class),
                rs.getString("capability"),
                rs.getString("origin_system"),
                rs.getString("external_reference"),
                amount,
                rs.getString("currency"),
                rs.getString("external_status"),
                rs.getString("delivery_status"),
                rs.getString("correlation_id"),
                rs.getString("spider_decision_id"),
                rs.getString("provider_reference"),
                rs.getString("provider_origin"),
                rs.getString("last_error"),
                observed == null ? null : observed.toInstant(),
                updated == null ? null : updated.toInstant(),
                attempted == null ? null : attempted.toInstant(),
                columnString(rs, "last_attempt_outcome"),
                rs.getObject("last_attempt_id", UUID.class),
                rs.getLong("version"),
                false,
                true);
    }

    private static Timestamp column(java.sql.ResultSet rs, String name) {
        try {
            return rs.getTimestamp(name);
        } catch (java.sql.SQLException ignored) {
            return null;
        }
    }

    private static String columnString(java.sql.ResultSet rs, String name) {
        try {
            return rs.getString(name);
        } catch (java.sql.SQLException ignored) {
            return null;
        }
    }
}
