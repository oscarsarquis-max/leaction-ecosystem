package br.com.actionfinance.application;

import br.com.actionfinance.domain.FoundationStage;

public record SystemInfo(
        String name,
        String version,
        FoundationStage stage,
        boolean financialOperationsAvailable,
        String spiderIntegrationStatus,
        boolean demoEnvironment,
        String accessMode) {}
