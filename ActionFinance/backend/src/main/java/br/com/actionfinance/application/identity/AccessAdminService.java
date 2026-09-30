package br.com.actionfinance.application.identity;

import br.com.actionfinance.infrastructure.persistence.JdbcIdentityRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class AccessAdminService {

    public record Result(boolean changed, String summary, UUID userId) {}

    private final JdbcIdentityRepository identities;
    private final Clock clock;

    public AccessAdminService(JdbcIdentityRepository identities, Clock clock) {
        this.identities = identities;
        this.clock = clock;
    }

    @Transactional
    public Result bootstrapOrganization(
            String tenantCode,
            String tenantName,
            String companyCode,
            String companyName,
            String businessTimezone,
            String responsibleName,
            String reason,
            String executorLabel,
            boolean dryRun) {
        requireText(tenantCode, "tenantCode");
        requireText(tenantName, "tenantName");
        requireText(companyCode, "companyCode");
        requireText(companyName, "companyName");
        requireText(businessTimezone, "businessTimezone");
        requireText(responsibleName, "responsibleName");
        requireText(reason, "reason");
        if (reason.trim().length() < 3) {
            throw new IllegalArgumentException("reason must have at least 3 characters.");
        }
        if (identities.tenantCodeExists(tenantCode.trim())) {
            throw new IllegalArgumentException("Tenant code already exists.");
        }
        Instant now = clock.instant();
        UUID tenantId = UUID.randomUUID();
        UUID companyId = UUID.randomUUID();
        if (!dryRun) {
            identities.insertTenant(tenantId, tenantCode.trim(), tenantName.trim(), now);
            identities.insertCompany(
                    companyId,
                    tenantId,
                    companyCode.trim(),
                    companyName.trim(),
                    businessTimezone.trim(),
                    now);
            audit(
                    now,
                    executorLabel,
                    "IDENTITY",
                    tenantId,
                    "PROVISION_USER",
                    reason,
                    null,
                    Map.of(
                            "kind",
                            "BOOTSTRAP_ORGANIZATION",
                            "responsibleName",
                            responsibleName.trim(),
                            "companyCode",
                            companyCode.trim(),
                            "tenantCode",
                            tenantCode.trim(),
                            "companyId",
                            companyId.toString()));
        }
        String summary =
                (dryRun ? "DRY-RUN " : "")
                        + "tenant "
                        + tenantCode.trim()
                        + " and company "
                        + companyCode.trim()
                        + " for "
                        + responsibleName.trim()
                        + ".";
        return new Result(true, summary + " tenantId=" + tenantId + " companyId=" + companyId, tenantId);
    }

    @Transactional
    public Result provision(
            String displayName,
            String issuer,
            String subject,
            UUID tenantId,
            UUID companyId,
            MembershipRole role,
            String reason,
            String executorLabel,
            String correlationId,
            boolean dryRun) {
        requireText(displayName, "displayName");
        requireText(issuer, "issuer");
        requireText(subject, "subject");
        requireId(tenantId, "tenantId");
        requireId(companyId, "companyId");
        requireText(reason, "reason");
        if (reason.trim().length() < 3) {
            throw new IllegalArgumentException("reason must have at least 3 characters.");
        }
        if (!identities.companyExists(tenantId, companyId)) {
            throw new IllegalArgumentException("Company is not in the requested tenant.");
        }
        Instant now = clock.instant();
        var existingIdentity = identities.findIdentity(issuer, subject);
        UUID userId = existingIdentity.map(IdentityRecords.ExternalIdentity::userId).orElseGet(UUID::randomUUID);
        boolean createdUser = existingIdentity.isEmpty();
        if (existingIdentity.isEmpty()) {
            if (!dryRun) {
                identities.insertUser(
                        new IdentityRecords.AppUser(
                                userId, displayName.trim(), UserStatus.ACTIVE, now, now, 0));
                identities.insertIdentity(UUID.randomUUID(), userId, issuer.trim(), subject.trim(), now);
                audit(
                        now,
                        executorLabel,
                        "USER",
                        userId,
                        "PROVISION_USER",
                        reason,
                        correlationId,
                        Map.of("issuerPresent", true, "subjectPresent", true));
                audit(
                        now,
                        executorLabel,
                        "IDENTITY",
                        userId,
                        "LINK_IDENTITY",
                        reason,
                        correlationId,
                        Map.of("linked", true));
            }
        }
        var membership = identities.findMembership(userId, tenantId, companyId);
        boolean membershipChanged;
        if (membership.isEmpty()) {
            membershipChanged = true;
            if (!dryRun) {
                identities.insertMembership(
                        new IdentityRecords.Membership(
                                UUID.randomUUID(),
                                userId,
                                tenantId,
                                companyId,
                                role,
                                "ACTIVE",
                                0),
                        now);
                audit(
                        now,
                        executorLabel,
                        "MEMBERSHIP",
                        userId,
                        "GRANT_MEMBERSHIP",
                        reason,
                        correlationId,
                        Map.of("role", role.name(), "companyId", companyId.toString()));
            }
        } else if (!"ACTIVE".equals(membership.get().status()) || membership.get().role() != role) {
            membershipChanged = true;
            if (!dryRun) {
                identities.updateMembership(
                        membership.get().id(), role, "ACTIVE", now, membership.get().version());
                audit(
                        now,
                        executorLabel,
                        "MEMBERSHIP",
                        userId,
                        "GRANT_MEMBERSHIP",
                        reason,
                        correlationId,
                        Map.of("role", role.name(), "reactivated", true));
            }
        } else {
            membershipChanged = false;
        }
        boolean changed = createdUser || membershipChanged;
        String summary =
                (dryRun ? "DRY-RUN " : "")
                        + (createdUser ? "provisioned user and identity; " : "reused identity; ")
                        + (membershipChanged ? "membership granted." : "membership unchanged.");
        return new Result(changed, summary, userId);
    }

    @Transactional
    public Result revoke(UUID userId, UUID tenantId, UUID companyId, String reason, String executorLabel, boolean dryRun) {
        requireId(userId, "userId");
        requireId(tenantId, "tenantId");
        requireId(companyId, "companyId");
        requireText(reason, "reason");
        var membership =
                identities
                        .findMembership(userId, tenantId, companyId)
                        .orElseThrow(() -> new IllegalArgumentException("Membership not found."));
        if ("REVOKED".equals(membership.status())) {
            return new Result(false, (dryRun ? "DRY-RUN " : "") + "membership already revoked.", userId);
        }
        if (!dryRun) {
            identities.updateMembership(
                    membership.id(), membership.role(), "REVOKED", clock.instant(), membership.version());
            audit(
                    clock.instant(),
                    executorLabel,
                    "MEMBERSHIP",
                    userId,
                    "REVOKE_MEMBERSHIP",
                    reason,
                    null,
                    Map.of("companyId", companyId.toString()));
        }
        return new Result(true, (dryRun ? "DRY-RUN " : "") + "membership revoked.", userId);
    }

    @Transactional
    public Result setBlocked(UUID userId, boolean blocked, String reason, String executorLabel, boolean dryRun) {
        requireId(userId, "userId");
        requireText(reason, "reason");
        var user = identities.findUser(userId).orElseThrow(() -> new IllegalArgumentException("User not found."));
        UserStatus next = blocked ? UserStatus.BLOCKED : UserStatus.ACTIVE;
        if (user.status() == next) {
            return new Result(false, (dryRun ? "DRY-RUN " : "") + "user status unchanged.", userId);
        }
        if (!dryRun) {
            identities.updateUserStatus(userId, next, clock.instant(), user.version());
            audit(
                    clock.instant(),
                    executorLabel,
                    "USER",
                    userId,
                    blocked ? "BLOCK_USER" : "UNBLOCK_USER",
                    reason,
                    null,
                    Map.of("status", next.name()));
        }
        return new Result(true, (dryRun ? "DRY-RUN " : "") + "user " + next.name().toLowerCase() + ".", userId);
    }

    private void audit(
            Instant now,
            String executorLabel,
            String targetKind,
            UUID targetId,
            String action,
            String reason,
            String correlationId,
            Map<String, Object> metadata) {
        identities.insertAudit(
                UUID.randomUUID(),
                now,
                "ADMIN_CLI",
                executorLabel == null || executorLabel.isBlank() ? "access-admin" : executorLabel.trim(),
                targetKind,
                targetId,
                action,
                reason.trim(),
                correlationId,
                toJson(metadata));
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " is required.");
        }
    }

    private static void requireId(UUID value, String name) {
        if (value == null) {
            throw new IllegalArgumentException(name + " is required.");
        }
    }

    private static String toJson(Map<String, Object> metadata) {
        StringBuilder json = new StringBuilder("{");
        boolean first = true;
        for (var entry : new LinkedHashMap<>(metadata).entrySet()) {
            if (!first) {
                json.append(',');
            }
            first = false;
            json.append('"')
                    .append(entry.getKey().replace("\"", ""))
                    .append("\":");
            Object value = entry.getValue();
            if (value instanceof Boolean || value instanceof Number) {
                json.append(value);
            } else {
                json.append('"').append(String.valueOf(value).replace("\"", "")).append('"');
            }
        }
        return json.append('}').toString();
    }
}
