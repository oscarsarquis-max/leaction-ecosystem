package br.com.actionfinance.infrastructure.persistence;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CompanyCnpjMigrationV27Test {

    @Test
    void v27OnlyAddsTheOptionalCompanyColumn() throws Exception {
        String sql = Files.readString(Path.of("..", "database", "migrations", "V27__company_cnpj.sql"));
        String lower = sql.toLowerCase();
        assertTrue(lower.contains("add column if not exists cnpj varchar(14)"));
        assertTrue(lower.contains("cnpj is null or cnpj ~ '^[0-9]{14}$'"));
        assertFalse(lower.contains("insert into"));
        assertFalse(lower.contains("update "));
        assertFalse(sql.chars().filter(Character::isDigit).count() > 20, "script must not carry a customer number");
    }
}
