package br.com.banco.spider.satellite.contract;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import java.io.InputStream;
import java.util.Map;
import java.util.Set;

public final class SatelliteContractSchema {

  private static final ObjectMapper MAPPER = new ObjectMapper();
  private static final JsonSchema REQUEST_1_0 =
      load("/contracts/satellite/1.0/satellite-interaction-request.schema.json");
  private static final JsonSchema REQUEST_1_1 =
      load("/contracts/satellite/1.1/satellite-interaction-request.schema.json");

  private SatelliteContractSchema() {}

  public static String validateRequest(Map<String, Object> body) {
    try {
      String version = body == null ? "" : String.valueOf(body.get("contractVersion"));
      JsonSchema schema = SatelliteContractV1.is11(version) ? REQUEST_1_1 : REQUEST_1_0;
      JsonNode node = MAPPER.valueToTree(body);
      Set<ValidationMessage> errors = schema.validate(node);
      if (errors.isEmpty()) {
        return null;
      }
      return errors.iterator().next().getMessage();
    } catch (RuntimeException e) {
      return "Payload inválido.";
    }
  }

  private static JsonSchema load(String path) {
    try (InputStream in = SatelliteContractSchema.class.getResourceAsStream(path)) {
      if (in == null) {
        throw new IllegalStateException("Missing schema " + path);
      }
      return JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012).getSchema(in);
    } catch (Exception e) {
      throw new IllegalStateException(e);
    }
  }
}
