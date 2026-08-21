package br.com.banco.spider.contracts;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import java.io.InputStream;
import java.util.Set;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class CanonicalJsonSchemaContractTest {

  private static final ObjectMapper MAPPER = new ObjectMapper();
  private static JsonSchema requestSchema;
  private static JsonSchema errorSchema;

  @BeforeAll
  static void loadSchemas() throws Exception {
    JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012);
    try (InputStream in =
        resource("/contracts/canonical/1.0/canonical-execution-request.schema.json")) {
      requestSchema = factory.getSchema(in);
    }
    try (InputStream in = resource("/contracts/canonical/1.0/canonical-error.schema.json")) {
      errorSchema = factory.getSchema(in);
    }
  }

  @Test
  void validRequestPassesSchema() throws Exception {
    JsonNode node = MAPPER.readTree(resource("/contracts/canonical/1.0/valid/request-minimal.json"));
    Set<ValidationMessage> errors = requestSchema.validate(node);
    assertTrue(errors.isEmpty(), errors::toString);
  }

  @Test
  void unknownFieldFailsSchema() throws Exception {
    JsonNode node =
        MAPPER.readTree(resource("/contracts/canonical/1.0/invalid/request-unknown-field.json"));
    Set<ValidationMessage> errors = requestSchema.validate(node);
    assertFalse(errors.isEmpty());
    assertTrue(
        errors.stream()
            .anyMatch(
                m -> {
                  String msg = m.getMessage().toLowerCase();
                  return msg.contains("additional")
                      || msg.contains("adicion")
                      || msg.contains("extraforbidden");
                }),
        errors::toString);
  }

  @Test
  void validErrorPassesSchema() throws Exception {
    JsonNode node = MAPPER.readTree(resource("/contracts/canonical/1.0/valid/error-sample.json"));
    Set<ValidationMessage> errors = errorSchema.validate(node);
    assertTrue(errors.isEmpty(), errors::toString);
  }

  private static InputStream resource(String path) {
    InputStream in = CanonicalJsonSchemaContractTest.class.getResourceAsStream(path);
    if (in == null) {
      throw new IllegalStateException("Missing classpath resource: " + path);
    }
    return in;
  }
}
