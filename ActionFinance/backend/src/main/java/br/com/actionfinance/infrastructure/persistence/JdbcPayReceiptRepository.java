package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.integration.PayReceiptViews.RevisionView;
import br.com.actionfinance.application.integration.PayReceiptViews.SyncRunView;
import br.com.actionfinance.application.integration.PayReceiptViews.TransactionView;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcPayReceiptRepository {

    public static final String ORIGIN = "ACTIONHUB_PAY";

    private final JdbcTemplate jdbc;

    public JdbcPayReceiptRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<String> authorizedEnvironment(AuthorizedScope scope) {
        List<String> rows =
                jdbc.query(
                        """
                        select environment from actionfinance.pay_company_mapping
                        where tenant_id = ? and company_id = ? and authorized = true
                        limit 1
                        """,
                        (rs, i) -> rs.getString("environment"),
                        scope.tenantId(),
                        scope.companyId());
        return rows.stream().findFirst();
    }

    public Optional<SyncRunView> findRunning(AuthorizedScope scope, String environment) {
        return firstRun(
                """
                select * from actionfinance.pay_receipt_sync_run
                where tenant_id = ? and company_id = ? and origin_system = ? and environment = ? and status = 'RUNNING'
                """,
                scope.tenantId(),
                scope.companyId(),
                ORIGIN,
                environment);
    }

    public Optional<SyncRunView> latestRun(AuthorizedScope scope, String environment) {
        return firstRun(
                """
                select * from actionfinance.pay_receipt_sync_run
                where tenant_id = ? and company_id = ? and origin_system = ? and environment = ?
                order by started_at desc
                limit 1
                """,
                scope.tenantId(),
                scope.companyId(),
                ORIGIN,
                environment);
    }

    public Optional<SyncRunView> findRun(AuthorizedScope scope, UUID runId) {
        return firstRun(
                """
                select * from actionfinance.pay_receipt_sync_run
                where tenant_id = ? and company_id = ? and id = ?
                """,
                scope.tenantId(),
                scope.companyId(),
                runId);
    }

    public Optional<Checkpoint> loadCheckpoint(AuthorizedScope scope, String environment) {
        List<Checkpoint> rows =
                jdbc.query(
                        """
                        select last_cursor, last_origin_updated_at, last_transaction_id, last_completed_run_id
                        from actionfinance.pay_receipt_checkpoint
                        where tenant_id = ? and company_id = ? and origin_system = ? and environment = ?
                        """,
                        (rs, i) ->
                                new Checkpoint(
                                        rs.getString("last_cursor"),
                                        ts(rs, "last_origin_updated_at"),
                                        rs.getString("last_transaction_id"),
                                        uuid(rs, "last_completed_run_id")),
                        scope.tenantId(),
                        scope.companyId(),
                        ORIGIN,
                        environment);
        return rows.stream().findFirst();
    }

    public boolean insertRunning(
            AuthorizedScope scope,
            UUID id,
            String environment,
            String correlationId,
            String startCursor,
            Instant now) {
        try {
            jdbc.update(
                    """
                    insert into actionfinance.pay_receipt_sync_run (
                        id, tenant_id, company_id, origin_system, environment, status,
                        root_correlation_id, start_cursor, resume_cursor, page_count,
                        imported_count, updated_count, review_count, started_at, created_at, updated_at)
                    values (?,?,?,?,?,'RUNNING',?,?,?,0,0,0,0,?,?,?)
                    """,
                    id,
                    scope.tenantId(),
                    scope.companyId(),
                    ORIGIN,
                    environment,
                    correlationId,
                    startCursor,
                    startCursor,
                    Timestamp.from(now),
                    Timestamp.from(now),
                    Timestamp.from(now));
            return true;
        } catch (DuplicateKeyException ignored) {
            return false;
        }
    }

    public void markPageApplied(
            AuthorizedScope scope,
            UUID runId,
            int pageNo,
            String cursorSent,
            String cursorNext,
            int itemCount,
            String correlationId,
            String spiderMessageId,
            int imported,
            int updated,
            int review,
            Instant now) {
        jdbc.update(
                """
                insert into actionfinance.pay_receipt_sync_page (
                    id, tenant_id, company_id, run_id, page_no, cursor_sent, cursor_next,
                    item_count, correlation_id, spider_message_id, outcome, created_at)
                values (?,?,?,?,?,?,?,?,?,?, 'APPLIED', ?)
                """,
                UUID.randomUUID(),
                scope.tenantId(),
                scope.companyId(),
                runId,
                pageNo,
                cursorSent,
                cursorNext,
                itemCount,
                correlationId,
                spiderMessageId,
                Timestamp.from(now));
        jdbc.update(
                """
                update actionfinance.pay_receipt_sync_run
                set resume_cursor = ?,
                    spider_message_id = coalesce(spider_message_id, ?),
                    page_count = page_count + 1,
                    imported_count = imported_count + ?,
                    updated_count = updated_count + ?,
                    review_count = review_count + ?,
                    updated_at = ?
                where id = ? and tenant_id = ? and company_id = ?
                """,
                cursorNext,
                spiderMessageId,
                imported,
                updated,
                review,
                Timestamp.from(now),
                runId,
                scope.tenantId(),
                scope.companyId());
    }

    public void attachMessage(AuthorizedScope scope, UUID runId, String spiderMessageId, Instant now) {
        if (spiderMessageId == null || spiderMessageId.isBlank()) {
            return;
        }
        jdbc.update(
                """
                update actionfinance.pay_receipt_sync_run
                set spider_message_id = coalesce(spider_message_id, ?), updated_at = ?
                where id = ? and tenant_id = ? and company_id = ?
                """,
                spiderMessageId,
                Timestamp.from(now),
                runId,
                scope.tenantId(),
                scope.companyId());
    }

    public int reclaimStaleRunning(AuthorizedScope scope, String environment, Instant olderThan, Instant now) {
        return jdbc.update(
                """
                update actionfinance.pay_receipt_sync_run
                set status = case when page_count > 0 then 'PARTIAL' else 'FAILED' end,
                    last_error = 'execução interrompida',
                    finished_at = ?,
                    updated_at = ?
                where tenant_id = ? and company_id = ? and origin_system = ? and environment = ?
                  and status = 'RUNNING' and updated_at < ?
                """,
                Timestamp.from(now),
                Timestamp.from(now),
                scope.tenantId(),
                scope.companyId(),
                ORIGIN,
                environment,
                Timestamp.from(olderThan));
    }

    public int reclaimAllRunning(Instant now) {
        return jdbc.update(
                """
                update actionfinance.pay_receipt_sync_run
                set status = case when page_count > 0 then 'PARTIAL' else 'FAILED' end,
                    last_error = 'execução interrompida',
                    finished_at = ?,
                    updated_at = ?
                where status = 'RUNNING'
                """,
                Timestamp.from(now),
                Timestamp.from(now));
    }

    public void finishRun(
            AuthorizedScope scope,
            UUID runId,
            String status,
            String error,
            Instant now) {
        jdbc.update(
                """
                update actionfinance.pay_receipt_sync_run
                set status = ?, last_error = ?, finished_at = ?, updated_at = ?
                where id = ? and tenant_id = ? and company_id = ?
                """,
                status,
                error,
                Timestamp.from(now),
                Timestamp.from(now),
                runId,
                scope.tenantId(),
                scope.companyId());
    }

    public void advanceCheckpoint(
            AuthorizedScope scope, String environment, String cursor, Instant originUpdatedAt, String transactionId, UUID runId, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.pay_receipt_checkpoint (
                    tenant_id, company_id, origin_system, environment,
                    last_origin_updated_at, last_transaction_id, last_cursor, last_completed_run_id, updated_at)
                values (?,?,?,?,?,?,?,?,?)
                on conflict (tenant_id, company_id, origin_system, environment) do update
                set last_origin_updated_at = excluded.last_origin_updated_at,
                    last_transaction_id = excluded.last_transaction_id,
                    last_cursor = excluded.last_cursor,
                    last_completed_run_id = excluded.last_completed_run_id,
                    updated_at = excluded.updated_at
                """,
                scope.tenantId(),
                scope.companyId(),
                ORIGIN,
                environment,
                originUpdatedAt == null ? null : Timestamp.from(originUpdatedAt),
                transactionId,
                cursor,
                runId,
                Timestamp.from(now));
    }

    public Optional<TransactionView> findByIdentity(
            AuthorizedScope scope, String environment, String transactionId) {
        List<TransactionView> rows =
                jdbc.query(
                        """
                        select * from actionfinance.pay_receipt_transaction
                        where tenant_id = ? and company_id = ? and origin_system = ? and environment = ? and transaction_id = ?
                        """,
                        this::mapTxn,
                        scope.tenantId(),
                        scope.companyId(),
                        ORIGIN,
                        environment,
                        transactionId);
        return rows.stream().findFirst();
    }

    public Optional<TransactionView> findById(AuthorizedScope scope, UUID id) {
        List<TransactionView> rows =
                jdbc.query(
                        """
                        select * from actionfinance.pay_receipt_transaction
                        where tenant_id = ? and company_id = ? and id = ?
                        """,
                        this::mapTxn,
                        scope.tenantId(),
                        scope.companyId(),
                        id);
        return rows.stream().findFirst();
    }

    public List<TransactionView> list(AuthorizedScope scope, String environment, int limit) {
        return jdbc.query(
                """
                select * from actionfinance.pay_receipt_transaction
                where tenant_id = ? and company_id = ? and origin_system = ? and environment = ?
                order by origin_updated_at desc nulls last, transaction_id desc
                limit ?
                """,
                this::mapTxn,
                scope.tenantId(),
                scope.companyId(),
                ORIGIN,
                environment,
                limit);
    }

    public List<RevisionView> revisions(AuthorizedScope scope, UUID transactionPk) {
        return jdbc.query(
                """
                select * from actionfinance.pay_receipt_transaction_revision
                where tenant_id = ? and company_id = ? and transaction_pk = ?
                order by observed_at desc
                """,
                (rs, i) ->
                        new RevisionView(
                                uuid(rs, "id"),
                                ts(rs, "observed_at"),
                                rs.getString("original_status"),
                                rs.getString("normalized_status"),
                                amountText(rs.getBigDecimal("amount_minor")),
                                rs.getString("currency"),
                                rs.getBoolean("review_required"),
                                ts(rs, "origin_revision"),
                                rs.getString("correlation_id")),
                scope.tenantId(),
                scope.companyId(),
                transactionPk);
    }

    public void insertTransaction(AuthorizedScope scope, TransactionView view) {
        jdbc.update(
                """
                insert into actionfinance.pay_receipt_transaction (
                    id, tenant_id, company_id, origin_system, environment, transaction_id, order_reference,
                    processor_reference, original_status, normalized_status, amount_minor, currency,
                    amount_absent, review_required, test_labeled, origin_created_at, origin_updated_at,
                    origin_revision, last_sync_run_id, last_correlation_id, created_at, updated_at)
                values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                view.id(),
                scope.tenantId(),
                scope.companyId(),
                ORIGIN,
                view.environment(),
                view.transactionId(),
                view.orderReference(),
                view.processorReference(),
                view.originalStatus(),
                view.normalizedStatus(),
                toAmount(view.amountMinor()),
                view.currency(),
                view.amountAbsent(),
                view.reviewRequired(),
                view.testLabeled(),
                ts(view.originCreatedAt()),
                ts(view.originUpdatedAt()),
                ts(view.originRevision()),
                view.lastSyncRunId(),
                view.lastCorrelationId(),
                Timestamp.from(view.updatedAt()),
                Timestamp.from(view.updatedAt()));
        insertRevision(scope, view);
    }

    public void updateTransaction(AuthorizedScope scope, TransactionView view) {
        jdbc.update(
                """
                update actionfinance.pay_receipt_transaction
                set order_reference = ?, processor_reference = ?, original_status = ?, normalized_status = ?,
                    amount_minor = ?, currency = ?, amount_absent = ?, review_required = ?, test_labeled = ?,
                    origin_created_at = ?, origin_updated_at = ?, origin_revision = ?,
                    last_sync_run_id = ?, last_correlation_id = ?, updated_at = ?
                where id = ? and tenant_id = ? and company_id = ?
                """,
                view.orderReference(),
                view.processorReference(),
                view.originalStatus(),
                view.normalizedStatus(),
                toAmount(view.amountMinor()),
                view.currency(),
                view.amountAbsent(),
                view.reviewRequired(),
                view.testLabeled(),
                ts(view.originCreatedAt()),
                ts(view.originUpdatedAt()),
                ts(view.originRevision()),
                view.lastSyncRunId(),
                view.lastCorrelationId(),
                Timestamp.from(view.updatedAt()),
                view.id(),
                scope.tenantId(),
                scope.companyId());
        insertRevision(scope, view);
    }

    public long countTitles(AuthorizedScope scope) {
        Long count =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.financial_title where tenant_id = ? and company_id = ?",
                        Long.class,
                        scope.tenantId(),
                        scope.companyId());
        return count == null ? 0 : count;
    }

    public long countSettlements(AuthorizedScope scope) {
        Long count =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.settlement where tenant_id = ? and company_id = ?",
                        Long.class,
                        scope.tenantId(),
                        scope.companyId());
        return count == null ? 0 : count;
    }

    public long countMovements(AuthorizedScope scope) {
        Long count =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.cash_movement where tenant_id = ? and company_id = ?",
                        Long.class,
                        scope.tenantId(),
                        scope.companyId());
        return count == null ? 0 : count;
    }

    private void insertRevision(AuthorizedScope scope, TransactionView view) {
        jdbc.update(
                """
                insert into actionfinance.pay_receipt_transaction_revision (
                    id, tenant_id, company_id, transaction_pk, original_status, normalized_status,
                    amount_minor, currency, review_required, origin_revision, sync_run_id, correlation_id, observed_at)
                values (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                UUID.randomUUID(),
                scope.tenantId(),
                scope.companyId(),
                view.id(),
                view.originalStatus(),
                view.normalizedStatus(),
                view.amountMinor() == null ? null : new BigDecimal(view.amountMinor()),
                view.currency(),
                view.reviewRequired(),
                ts(view.originRevision()),
                view.lastSyncRunId(),
                view.lastCorrelationId(),
                Timestamp.from(view.updatedAt()));
    }

    private Optional<SyncRunView> firstRun(String sql, Object... args) {
        List<SyncRunView> rows = jdbc.query(sql, this::mapRun, args);
        return rows.stream().findFirst();
    }

    private SyncRunView mapRun(ResultSet rs, int i) throws SQLException {
        return new SyncRunView(
                uuid(rs, "id"),
                rs.getString("environment"),
                rs.getString("status"),
                rs.getString("root_correlation_id"),
                rs.getString("spider_message_id"),
                rs.getString("resume_cursor"),
                rs.getInt("page_count"),
                rs.getInt("imported_count"),
                rs.getInt("updated_count"),
                rs.getInt("review_count"),
                rs.getString("last_error"),
                ts(rs, "started_at"),
                ts(rs, "finished_at"),
                null);
    }

    private TransactionView mapTxn(ResultSet rs, int i) throws SQLException {
        return new TransactionView(
                uuid(rs, "id"),
                uuid(rs, "company_id"),
                rs.getString("environment"),
                rs.getString("transaction_id"),
                rs.getString("order_reference"),
                rs.getString("processor_reference"),
                rs.getString("original_status"),
                rs.getString("normalized_status"),
                amount(rs),
                rs.getString("currency"),
                rs.getBoolean("amount_absent"),
                rs.getBoolean("review_required"),
                rs.getBoolean("test_labeled"),
                ts(rs, "origin_created_at"),
                ts(rs, "origin_updated_at"),
                ts(rs, "origin_revision"),
                uuid(rs, "last_sync_run_id"),
                rs.getString("last_correlation_id"),
                ts(rs, "updated_at"));
    }

    private static String amount(ResultSet rs) throws SQLException {
        return amountText(rs.getBigDecimal("amount_minor"));
    }

    private static String amountText(BigDecimal value) {
        return value == null ? null : value.toPlainString();
    }

    private static BigDecimal toAmount(String value) {
        return value == null || value.isBlank() ? null : new BigDecimal(value);
    }

    private static Timestamp ts(Instant value) {
        return value == null ? null : Timestamp.from(value);
    }

    private static Instant ts(ResultSet rs, String column) throws SQLException {
        Timestamp value = rs.getTimestamp(column);
        return value == null ? null : value.toInstant();
    }

    private static UUID uuid(ResultSet rs, String column) throws SQLException {
        return rs.getObject(column, UUID.class);
    }

    public record Checkpoint(String cursor, Instant originUpdatedAt, String transactionId, UUID completedRunId) {}
}
