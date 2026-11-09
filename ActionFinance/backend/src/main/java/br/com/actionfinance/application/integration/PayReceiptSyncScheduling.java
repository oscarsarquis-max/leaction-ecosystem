package br.com.actionfinance.application.integration;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

@Configuration
@EnableScheduling
@Profile("production")
@ConditionalOnProperty(prefix = "actionfinance.pay-sync", name = "scheduler-enabled", havingValue = "true")
public class PayReceiptSyncScheduling {

    private final PayReceiptSyncCycle cycle;

    public PayReceiptSyncScheduling(PayReceiptSyncCycle cycle) {
        this.cycle = cycle;
    }

    @Scheduled(fixedDelayString = "${actionfinance.pay-sync.interval:30m}")
    public void tick() {
        cycle.run();
    }
}
