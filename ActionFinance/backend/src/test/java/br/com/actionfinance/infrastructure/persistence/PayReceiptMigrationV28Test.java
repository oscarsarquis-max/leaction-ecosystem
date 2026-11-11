package br.com.actionfinance.infrastructure.persistence;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PayReceiptMigrationV28Test {

    @Test
    void v28AddsOnlyNullablePayerColumnsWithoutBackfill() throws Exception {
        String sql =
                Files.readString(Path.of("..", "database", "migrations", "V28__pay_receipt_payer_fields.sql"));
        for (String column :
                List.of(
                        "payer_name VARCHAR(200)",
                        "payer_email VARCHAR(200)",
                        "store_order_reference VARCHAR(80)",
                        "store_payment_request_id VARCHAR(80)",
                        "processor_payment_id VARCHAR(80)",
                        "purchase_description VARCHAR(200)",
                        "processor_approved_at VARCHAR(64)",
                        "processor_installments INTEGER")) {
            assertTrue(sql.contains("ADD COLUMN " + column), column);
        }
        String lower = sql.toLowerCase();
        assertFalse(lower.contains("default"));
        assertFalse(lower.contains("not null"));
        assertFalse(lower.contains("insert into"));
        assertFalse(lower.contains("update actionfinance"));
        assertFalse(lower.contains("financial_title"));
        assertFalse(lower.contains("settlement"));
        assertFalse(lower.contains("cash_movement"));
    }
}
