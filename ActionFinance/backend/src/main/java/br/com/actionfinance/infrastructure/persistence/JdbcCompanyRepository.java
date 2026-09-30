package br.com.actionfinance.infrastructure.persistence;

import br.com.actionfinance.application.finance.CompanyView;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcCompanyRepository implements br.com.actionfinance.application.finance.CompanyCatalog {

    private final JdbcTemplate jdbc;

    public JdbcCompanyRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final RowMapper<CompanyView> MAPPER = (rs, rowNum) -> new CompanyView(
            rs.getObject("id", UUID.class),
            rs.getObject("tenant_id", UUID.class),
            rs.getString("code"),
            rs.getString("name"),
            rs.getBoolean("active"),
            rs.getBoolean("is_demo"),
            rs.getString("business_timezone"));

    public Optional<CompanyView> findById(UUID companyId) {
        List<CompanyView> rows = jdbc.query(
                """
                select id, tenant_id, code, name, active, is_demo, business_timezone
                from actionfinance.company
                where id = ?
                """,
                MAPPER,
                companyId);
        return rows.stream().findFirst();
    }

    public List<CompanyView> findByIds(List<UUID> ids) {
        if (ids.isEmpty()) {
            return List.of();
        }
        String placeholders = String.join(",", ids.stream().map(id -> "?").toList());
        return jdbc.query(
                """
                select id, tenant_id, code, name, active, is_demo, business_timezone
                from actionfinance.company
                where id in (%s)
                order by name, id
                """
                        .formatted(placeholders),
                MAPPER,
                ids.toArray());
    }
}
