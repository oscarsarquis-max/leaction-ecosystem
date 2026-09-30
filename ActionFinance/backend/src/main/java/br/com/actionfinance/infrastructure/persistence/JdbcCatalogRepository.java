package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.CatalogRecords.CategoryView;
import br.com.actionfinance.application.finance.CatalogRecords.CounterpartyView;
import br.com.actionfinance.domain.CategoryDirection;
import br.com.actionfinance.domain.CounterpartyRole;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcCatalogRepository {

    private final JdbcTemplate jdbc;

    public JdbcCatalogRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final RowMapper<CounterpartyView> COUNTERPARTY = (rs, rowNum) -> new CounterpartyView(
            rs.getObject("id", UUID.class),
            rs.getObject("tenant_id", UUID.class),
            rs.getObject("company_id", UUID.class),
            rs.getString("code"),
            rs.getString("name"),
            CounterpartyRole.valueOf(rs.getString("role")),
            rs.getBoolean("active"),
            rs.getLong("version"),
            rs.getTimestamp("created_at").toInstant(),
            rs.getTimestamp("updated_at").toInstant());

    private static final RowMapper<CategoryView> CATEGORY = (rs, rowNum) -> new CategoryView(
            rs.getObject("id", UUID.class),
            rs.getObject("tenant_id", UUID.class),
            rs.getObject("company_id", UUID.class),
            rs.getString("code"),
            rs.getString("name"),
            CategoryDirection.valueOf(rs.getString("direction")),
            rs.getBoolean("active"),
            rs.getLong("version"),
            rs.getTimestamp("created_at").toInstant(),
            rs.getTimestamp("updated_at").toInstant());

    public List<CounterpartyView> listCounterparties(AuthorizedScope scope) {
        return jdbc.query(
                """
                select * from actionfinance.counterparty
                where tenant_id = ? and company_id = ?
                order by name, id
                """,
                COUNTERPARTY,
                scope.tenantId(),
                scope.companyId());
    }

    public Optional<CounterpartyView> findCounterparty(AuthorizedScope scope, UUID id) {
        List<CounterpartyView> rows = jdbc.query(
                """
                select * from actionfinance.counterparty
                where tenant_id = ? and company_id = ? and id = ?
                """,
                COUNTERPARTY,
                scope.tenantId(),
                scope.companyId(),
                id);
        return rows.stream().findFirst();
    }

    public Optional<CounterpartyView> lockCounterparty(AuthorizedScope scope, UUID id) {
        List<CounterpartyView> rows = jdbc.query(
                """
                select * from actionfinance.counterparty
                where tenant_id = ? and company_id = ? and id = ?
                for update
                """,
                COUNTERPARTY,
                scope.tenantId(),
                scope.companyId(),
                id);
        return rows.stream().findFirst();
    }

    public void insertCounterparty(CounterpartyView row, UUID actorId) {
        jdbc.update(
                """
                insert into actionfinance.counterparty (
                    id, tenant_id, company_id, code, name, role, active, version,
                    created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                row.id(),
                row.tenantId(),
                row.companyId(),
                row.code(),
                row.name(),
                row.role().name(),
                row.active(),
                row.version(),
                Timestamp.from(row.createdAt()),
                Timestamp.from(row.updatedAt()),
                actorId,
                actorId);
    }

    public int updateCounterparty(AuthorizedScope scope, UUID id, String name, Boolean active, long expectedVersion, Instant now, UUID actorId) {
        return jdbc.update(
                """
                update actionfinance.counterparty
                set name = coalesce(?, name),
                    active = coalesce(?, active),
                    version = version + 1,
                    updated_at = ?,
                    updated_by = ?
                where tenant_id = ? and company_id = ? and id = ? and version = ?
                """,
                name,
                active,
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                id,
                expectedVersion);
    }

    public boolean counterpartyHasTitles(AuthorizedScope scope, UUID id) {
        Integer count = jdbc.queryForObject(
                """
                select count(*) from actionfinance.financial_title
                where tenant_id = ? and company_id = ? and counterparty_id = ?
                """,
                Integer.class,
                scope.tenantId(),
                scope.companyId(),
                id);
        return count != null && count > 0;
    }

    public List<CategoryView> listCategories(AuthorizedScope scope) {
        return jdbc.query(
                """
                select * from actionfinance.financial_category
                where tenant_id = ? and company_id = ?
                order by name, id
                """,
                CATEGORY,
                scope.tenantId(),
                scope.companyId());
    }

    public Optional<CategoryView> findCategory(AuthorizedScope scope, UUID id) {
        List<CategoryView> rows = jdbc.query(
                """
                select * from actionfinance.financial_category
                where tenant_id = ? and company_id = ? and id = ?
                """,
                CATEGORY,
                scope.tenantId(),
                scope.companyId(),
                id);
        return rows.stream().findFirst();
    }

    public Optional<CategoryView> lockCategory(AuthorizedScope scope, UUID id) {
        List<CategoryView> rows = jdbc.query(
                """
                select * from actionfinance.financial_category
                where tenant_id = ? and company_id = ? and id = ?
                for update
                """,
                CATEGORY,
                scope.tenantId(),
                scope.companyId(),
                id);
        return rows.stream().findFirst();
    }

    public void insertCategory(CategoryView row, UUID actorId) {
        jdbc.update(
                """
                insert into actionfinance.financial_category (
                    id, tenant_id, company_id, code, name, direction, active, version,
                    created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                row.id(),
                row.tenantId(),
                row.companyId(),
                row.code(),
                row.name(),
                row.direction().name(),
                row.active(),
                row.version(),
                Timestamp.from(row.createdAt()),
                Timestamp.from(row.updatedAt()),
                actorId,
                actorId);
    }

    public int updateCategory(AuthorizedScope scope, UUID id, String name, Boolean active, long expectedVersion, Instant now, UUID actorId) {
        return jdbc.update(
                """
                update actionfinance.financial_category
                set name = coalesce(?, name),
                    active = coalesce(?, active),
                    version = version + 1,
                    updated_at = ?,
                    updated_by = ?
                where tenant_id = ? and company_id = ? and id = ? and version = ?
                """,
                name,
                active,
                Timestamp.from(now),
                actorId,
                scope.tenantId(),
                scope.companyId(),
                id,
                expectedVersion);
    }

    public boolean categoryHasTitles(AuthorizedScope scope, UUID id) {
        Integer count = jdbc.queryForObject(
                """
                select count(*) from actionfinance.financial_title
                where tenant_id = ? and company_id = ? and category_id = ?
                """,
                Integer.class,
                scope.tenantId(),
                scope.companyId(),
                id);
        return count != null && count > 0;
    }
}
