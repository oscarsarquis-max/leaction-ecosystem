package br.com.actionfinance.application.identity;

import java.time.Instant;
import java.util.UUID;

public final class IdentityRecords {

    public record AppUser(
            UUID id, String displayName, UserStatus status, Instant createdAt, Instant updatedAt, long version) {}

    public record ExternalIdentity(UUID id, UUID userId, String issuer, String subject) {}

    public record Membership(
            UUID id,
            UUID userId,
            UUID tenantId,
            UUID companyId,
            MembershipRole role,
            String status,
            long version) {}

    private IdentityRecords() {}
}
