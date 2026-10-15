package br.com.actionfinance.infrastructure.persistence;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PayReceiptMigrationV20Test {

    @Test
    void v20OnlyAddsTheColumnsTheReceiptMapperReads() throws Exception {
        String sql =
                Files.readString(
                        Path.of("..", "database", "migrations", "V20__pay_receipt_commercial_identity.sql"));
        for (String column :
                List.of(
                        "commercial_application",
                        "commercial_description",
                        "payer_kind",
                        "payer_label",
                        "payer_provenance",
                        "payment_method",
                        "processor_name",
                        "provider_status")) {
            assertTrue(sql.contains("ADD COLUMN " + column + " "), column);
        }
        String lower = sql.toLowerCase();
        assertFalse(lower.contains("financial_title"));
        assertFalse(lower.contains("settlement"));
        assertFalse(lower.contains("cash_movement"));
        assertFalse(lower.contains("insert into"));
    }
}
