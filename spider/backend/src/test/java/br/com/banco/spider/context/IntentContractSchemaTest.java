package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.context.domain.StaticBusinessIntentCatalog;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import java.io.InputStream;
import org.junit.jupiter.api.Test;

class IntentContractSchemaTest {

  private final ObjectMapper mapper = new ObjectMapper().findAndRegisterModules();

  @Test
  void businessCardContractMatchesVersionedSchema() {
    var contract =
        new StaticBusinessIntentCatalog()
            .findByIntent("INVESTIGATE_CREDIT_RELEASE")
            .orElseThrow()
            .businessCardContract();
    assertTrue(schema().validate(mapper.valueToTree(contract)).isEmpty());
  }

  @Test
  void schemaRejectsUnknownFieldsAndWrongVersion() throws Exception {
    var invalid =
        mapper.readTree(
            """
            {
              "schemaVersion":"2.0",
              "intent":"INVESTIGATE_CREDIT_RELEASE",
              "domain":"CREDIT",
              "objective":"IDENTIFY_BLOCKING_CONDITION",
              "entities":{"proposalId":"DEMO"},
              "constraints":{"mutationAllowed":false,"readOnly":true,"confirmationRequired":true},
              "provenance":{"source":"BUSINESS_CARD"},
              "confidence":1.0,
              "endpoint":"/forbidden"
            }
            """);
    assertFalse(schema().validate(invalid).isEmpty());
  }

  private static com.networknt.schema.JsonSchema schema() {
    InputStream in =
        IntentContractSchemaTest.class.getResourceAsStream(
            "/context/intent-contract-v1.schema.json");
    if (in == null) {
      throw new IllegalStateException("Intent Contract schema not found");
    }
    return JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012).getSchema(in);
  }
}
