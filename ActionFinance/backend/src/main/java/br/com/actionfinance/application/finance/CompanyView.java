package br.com.actionfinance.application.finance;

import java.util.UUID;

public record CompanyView(
        UUID id,
        UUID tenantId,
        String code,
        String name,
        boolean active,
        boolean demo,
        String businessTimezone) {}
