package br.com.actionfinance.infrastructure.persistence;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class OverviewStoreIsolationTest {

    @Test
    void everyReadNamesTheSessionTenantAndCompany() throws Exception {
        String source = Files.readString(Path.of(
                "src", "main", "java", "br", "com", "actionfinance", "infrastructure", "persistence", "JdbcOverviewStore.java"));
        Matcher queries = Pattern.compile("\"\"\"(.*?)\"\"\"", Pattern.DOTALL).matcher(source);
        int seen = 0;
        while (queries.find()) {
            String sql = queries.group(1).toLowerCase();
            seen++;
            assertTrue(sql.contains("tenant_id = ?"), sql);
            assertTrue(sql.contains("company_id = ?"), sql);
        }
        assertTrue(seen >= 10);
        assertTrue(source.contains("count(*)::int"));
        assertTrue(source.contains("kind = 'OPENING'"));
    }

    @Test
    void confirmedStatementWithoutATimestampIsAbsence() {
        List<Instant> row = new ArrayList<>();
        row.add(null);
        assertNull(JdbcOverviewStore.singleInstant(row));
        assertEquals(Instant.parse("2026-11-10T18:00:00Z"), JdbcOverviewStore.singleInstant(List.of(Instant.parse("2026-11-10T18:00:00Z"))));
    }

    @Test
    void aFailedBlockDoesNotEscape() {
        assertEquals(List.of(), JdbcOverviewStore.block("fees", List.of(), () -> {
            throw new IllegalStateException("statement");
        }));
    }
}
