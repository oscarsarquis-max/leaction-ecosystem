package br.com.actionfinance.application.identity;

import java.util.Set;
import java.util.UUID;

public record AuthorizedCompany(
        UUID id,
        UUID tenantId,
        String code,
        String name,
        boolean active,
        boolean demo,
        String businessTimezone,
        MembershipRole role,
        Set<String> permissions) {}
