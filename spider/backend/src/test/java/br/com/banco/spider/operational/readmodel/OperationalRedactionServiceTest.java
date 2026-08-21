package br.com.banco.spider.operational.readmodel;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class OperationalRedactionServiceTest {

  private final OperationalRedactionService service = new OperationalRedactionService();

  @Test
  void removesSensitiveKeysAndNestedSecrets() {
    Map<String, Object> hostile = new LinkedHashMap<>();
    hostile.put("customerRef", "C-1");
    hostile.put("token", "jwt.raw.should.never.appear");
    hostile.put("secret", "s3cr3t");
    hostile.put("password", "p");
    hostile.put("authorization", "Bearer x");
    hostile.put("mac", "deadbeef");
    hostile.put("nonce", "n");
    hostile.put("ciphertext", "c");
    hostile.put("iv", "iv");
    hostile.put("key", "k");
    hostile.put(
        "nested",
        Map.of("access_token", "x", "safeField", "ok", "children", List.of(Map.of("api_key", "z"))));

    var result = service.redact(hostile, 6, 64);
    assertFalse(result.projection().containsKey("token"));
    assertFalse(result.projection().containsKey("secret"));
    assertFalse(result.projection().containsKey("password"));
    assertFalse(result.projection().containsKey("authorization"));
    assertFalse(result.projection().containsKey("mac"));
    assertFalse(result.projection().containsKey("nonce"));
    assertFalse(result.projection().containsKey("ciphertext"));
    assertFalse(result.projection().containsKey("iv"));
    assertFalse(result.projection().containsKey("key"));
    assertEquals("C-1", result.projection().get("customerRef"));
    assertTrue(result.redactedFieldsCount() > 0);
    @SuppressWarnings("unchecked")
    Map<String, Object> nested = (Map<String, Object>) result.projection().get("nested");
    assertEquals("ok", nested.get("safeField"));
    assertFalse(nested.containsKey("access_token"));
  }

  @Test
  void truncatesOversizedStrings() {
    Map<String, Object> input = Map.of("note", "x".repeat(500));
    var result = service.redact(input, 4, 32);
    String note = (String) result.projection().get("note");
    assertTrue(note.contains("[TRUNCATED]"));
    assertTrue(note.length() < 60);
  }
}
