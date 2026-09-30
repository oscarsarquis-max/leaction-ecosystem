package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.identity.IdentityRecords.AppUser;
import br.com.actionfinance.application.identity.IdentityRecords.ExternalIdentity;
import br.com.actionfinance.application.identity.IdentityRecords.Membership;
import br.com.actionfinance.application.identity.MembershipRole;
import br.com.actionfinance.application.identity.UserStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcIdentityRepository {

    private final JdbcTemplate jdbc;

    public JdbcIdentityRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<ExternalIdentity> findIdentity(String issuer, String subject) {
        List<ExternalIdentity> rows =
                jdbc.query(
                        """
                        select id, user_id, issuer, subject
                          from actionfinance.external_identity
                         where issuer = ? and subject = ?
                        """,
                        identityMapper(),
                        issuer,
                        subject);
        return rows.stream().findFirst();
    }

    public Optional<AppUser> findUser(UUID id) {
        List<AppUser> rows =
                jdbc.query(
                        """
                        select id, display_name, status, created_at, updated_at, version
                          from actionfinance.app_user
                         where id = ?
                        """,
                        userMapper(),
                        id);
        return rows.stream().findFirst();
    }

    public List<Membership> listMemberships(UUID userId) {
        return jdbc.query(
                """
                select id, user_id, tenant_id, company_id, role, status, version
                  from actionfinance.company_membership
                 where user_id = ?
                """,
                membershipMapper(),
                userId);
    }

    public List<Membership> listActiveMemberships(UUID userId) {
        return jdbc.query(
                """
                select id, user_id, tenant_id, company_id, role, status, version
                  from actionfinance.company_membership
                 where user_id = ? and status = 'ACTIVE'
                """,
                membershipMapper(),
                userId);
    }

    public Optional<Membership> findMembership(UUID userId, UUID tenantId, UUID companyId) {
        List<Membership> rows =
                jdbc.query(
                        """
                        select id, user_id, tenant_id, company_id, role, status, version
                          from actionfinance.company_membership
                         where user_id = ? and tenant_id = ? and company_id = ?
                        """,
                        membershipMapper(),
                        userId,
                        tenantId,
                        companyId);
        return rows.stream().findFirst();
    }

    public boolean tenantCodeExists(String code) {
        Integer count =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.tenant where code = ?",
                        Integer.class,
                        code);
        return count != null && count > 0;
    }

    public boolean companyCodeExists(UUID tenantId, String code) {
        Integer count =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.company where tenant_id = ? and code = ?",
                        Integer.class,
                        tenantId,
                        code);
        return count != null && count > 0;
    }

    public void insertTenant(UUID id, String code, String name, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.tenant (id, code, name, active, created_at, updated_at, version)
                values (?, ?, ?, true, ?, ?, 1)
                """,
                id,
                code,
                name,
                Timestamp.from(now),
                Timestamp.from(now));
    }

    public void insertCompany(UUID id, UUID tenantId, String code, String name, String timezone, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.company (
                    id, tenant_id, code, name, active, is_demo, business_timezone, created_at, updated_at, version)
                values (?, ?, ?, ?, true, false, ?, ?, ?, 1)
                """,
                id,
                tenantId,
                code,
                name,
                timezone,
                Timestamp.from(now),
                Timestamp.from(now));
    }

    public boolean companyExists(UUID tenantId, UUID companyId) {
        Integer count =
                jdbc.queryForObject(
                        """
                        select count(*) from actionfinance.company
                         where tenant_id = ? and id = ?
                        """,
                        Integer.class,
                        tenantId,
                        companyId);
        return count != null && count > 0;
    }

    public void insertUser(AppUser user) {
        jdbc.update(
                """
                insert into actionfinance.app_user (
                    id, display_name, status, created_at, updated_at, version)
                values (?, ?, ?, ?, ?, ?)
                """,
                user.id(),
                user.displayName(),
                user.status().name(),
                Timestamp.from(user.createdAt()),
                Timestamp.from(user.updatedAt()),
                user.version());
    }

    public void updateUserStatus(UUID id, UserStatus status, Instant updatedAt, long expectedVersion) {
        int updated =
                jdbc.update(
                        """
                        update actionfinance.app_user
                           set status = ?, updated_at = ?, version = version + 1
                         where id = ? and version = ?
                        """,
                        status.name(),
                        Timestamp.from(updatedAt),
                        id,
                        expectedVersion);
        if (updated != 1) {
            throw new IllegalStateException("User version conflict.");
        }
    }

    public void insertIdentity(UUID id, UUID userId, String issuer, String subject, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.external_identity (
                    id, user_id, issuer, subject, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                id,
                userId,
                issuer,
                subject,
                Timestamp.from(now),
                Timestamp.from(now));
    }

    public void insertMembership(Membership membership, Instant now) {
        jdbc.update(
                """
                insert into actionfinance.company_membership (
                    id, user_id, tenant_id, company_id, role, status, created_at, updated_at, version)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                membership.id(),
                membership.userId(),
                membership.tenantId(),
                membership.companyId(),
                membership.role().name(),
                membership.status(),
                Timestamp.from(now),
                Timestamp.from(now),
                membership.version());
    }

    public void updateMembership(
            UUID id, MembershipRole role, String status, Instant updatedAt, long expectedVersion) {
        int updated =
                jdbc.update(
                        """
                        update actionfinance.company_membership
                           set role = ?, status = ?, updated_at = ?, version = version + 1
                         where id = ? and version = ?
                        """,
                        role.name(),
                        status,
                        Timestamp.from(updatedAt),
                        id,
                        expectedVersion);
        if (updated != 1) {
            throw new IllegalStateException("Membership version conflict.");
        }
    }

    public void insertAudit(
            UUID id,
            Instant occurredAt,
            String executorKind,
            String executorLabel,
            String targetKind,
            UUID targetId,
            String action,
            String reason,
            String correlationId,
            String metadataJson) {
        jdbc.update(
                """
                insert into actionfinance.access_admin_audit (
                    id, occurred_at, executor_kind, executor_label, target_kind, target_id,
                    action, reason, correlation_id, metadata)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)
                """,
                id,
                Timestamp.from(occurredAt),
                executorKind,
                executorLabel,
                targetKind,
                targetId,
                action,
                reason,
                correlationId,
                metadataJson);
    }

    private static RowMapper<AppUser> userMapper() {
        return (ResultSet rs, int rowNum) ->
                new AppUser(
                        rs.getObject("id", UUID.class),
                        rs.getString("display_name"),
                        UserStatus.valueOf(rs.getString("status")),
                        rs.getTimestamp("created_at").toInstant(),
                        rs.getTimestamp("updated_at").toInstant(),
                        rs.getLong("version"));
    }

    private static RowMapper<ExternalIdentity> identityMapper() {
        return (ResultSet rs, int rowNum) ->
                new ExternalIdentity(
                        rs.getObject("id", UUID.class),
                        rs.getObject("user_id", UUID.class),
                        rs.getString("issuer"),
                        rs.getString("subject"));
    }

    private static RowMapper<Membership> membershipMapper() {
        return (ResultSet rs, int rowNum) ->
                new Membership(
                        rs.getObject("id", UUID.class),
                        rs.getObject("user_id", UUID.class),
                        rs.getObject("tenant_id", UUID.class),
                        rs.getObject("company_id", UUID.class),
                        MembershipRole.valueOf(rs.getString("role")),
                        rs.getString("status"),
                        rs.getLong("version"));
    }
}
