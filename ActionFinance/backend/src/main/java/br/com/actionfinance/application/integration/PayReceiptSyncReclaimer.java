package br.com.actionfinance.application.integration;

import br.com.actionfinance.infrastructure.persistence.JdbcPayReceiptRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.time.Instant;

@Component
public class PayReceiptSyncReclaimer {

    private static final Logger log = LoggerFactory.getLogger(PayReceiptSyncReclaimer.class);

    private final JdbcPayReceiptRepository receipts;

    public PayReceiptSyncReclaimer(JdbcPayReceiptRepository receipts) {
        this.receipts = receipts;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void reclaimOrphansAfterRestart() {
        int reclaimed = receipts.reclaimAllRunning(Instant.now());
        if (reclaimed > 0) {
            log.info("pay_receipt_sync orphan RUNNING reclaimed count={}", reclaimed);
        }
    }
}
