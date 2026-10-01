package br.com.actionfinance.application;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.domain.FoundationStage;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;

import java.util.Arrays;

@Service
public class SystemInfoService {

    private final Environment environment;
    private final ActionFinanceProperties properties;

    public SystemInfoService(Environment environment, ActionFinanceProperties properties) {
        this.environment = environment;
        this.properties = properties;
    }

    public SystemInfo current() {
        boolean demo = Arrays.asList(environment.getActiveProfiles()).contains("local-demo");
        String accessMode = properties.getOidc().isEnabled() ? "OIDC" : demo ? "DEMO" : "NONE";
        boolean homolog = properties.getIntegration().isHomolog();
        boolean receiptSync = properties.getIntegration().isReceiptSyncEnabled();
        String spiderStatus = homolog ? "HOMOLOG_LOOKUP" : receiptSync ? "RECEIPT_SYNC" : "NOT_IMPLEMENTED";
        return new SystemInfo(
                "ActionFinance",
                environment.getProperty("actionfinance.app.version", "0.1.0"),
                FoundationStage.FOUNDATION,
                true,
                spiderStatus,
                demo,
                accessMode,
                homolog,
                receiptSync,
                properties.getIntegration().getSpiderMonitorBaseUrl());
    }
}
