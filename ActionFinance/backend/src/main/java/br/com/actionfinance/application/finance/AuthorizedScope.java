package br.com.actionfinance.application.finance;

import java.util.UUID;

public record AuthorizedScope(UUID tenantId, UUID companyId) {}
