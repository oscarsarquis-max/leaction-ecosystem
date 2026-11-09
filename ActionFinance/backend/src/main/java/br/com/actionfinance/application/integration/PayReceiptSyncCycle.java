package br.com.actionfinance.application.integration;

import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.infrastructure.persistence.JdbcPayReceiptRepository;
import br.com.actionfinance.infrastructure.persistence.JdbcPayReceiptRepository.CompanyBinding;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

@Service
public class PayReceiptSyncCycle {

    public static final long LOCK_KEY = 57057101L;

    private static final Logger log = LoggerFactory.getLogger(PayReceiptSyncCycle.class);

    private final ActionFinanceProperties properties;
    private final JdbcTemplate jdbc;
    private final JdbcPayReceiptRepository receipts;
    private final PayReceiptSyncService sync;

    public PayReceiptSyncCycle(
            ActionFinanceProperties properties,
            JdbcTemplate jdbc,
            JdbcPayReceiptRepository receipts,
            PayReceiptSyncService sync) {
        this.properties = properties;
        this.jdbc = jdbc;
        this.receipts = receipts;
        this.sync = sync;
    }

    public void run() {
        if (!properties.getIntegration().isReceiptSyncAllowed()) {
            log.info("pay-sync cycle skipped: receipt sync disabled");
            return;
        }
        jdbc.execute(
                (ConnectionCallback<Void>)
                        connection -> {
                            if (!tryLock(connection)) {
                                log.info("pay-sync cycle skipped: lock held");
                                return null;
                            }
                            try {
                                for (CompanyBinding company : receipts.listAuthorizedCompanies()) {
                                    synchronizeOne(company);
                                }
                            } finally {
                                unlock(connection);
                            }
                            return null;
                        });
    }

    private void synchronizeOne(CompanyBinding company) {
        try {
            sync.synchronizeAutomatic(new AuthorizedScope(company.tenantId(), company.companyId()));
        } catch (VersionConflictException exception) {
            log.info("pay-sync company={} skipped: sync already running", company.companyId());
        } catch (RuntimeException exception) {
            log.warn("pay-sync company={} failed: {}", company.companyId(), clip(exception.getMessage()));
        }
    }

    private static boolean tryLock(Connection connection) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("select pg_try_advisory_lock(?)")) {
            statement.setLong(1, LOCK_KEY);
            try (ResultSet result = statement.executeQuery()) {
                return result.next() && result.getBoolean(1);
            }
        }
    }

    private static void unlock(Connection connection) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("select pg_advisory_unlock(?)")) {
            statement.setLong(1, LOCK_KEY);
            statement.execute();
        }
    }

    private static String clip(String value) {
        if (value == null || value.isBlank()) {
            return "falha sem detalhe";
        }
        return value.length() > 200 ? value.substring(0, 200) : value;
    }
}
