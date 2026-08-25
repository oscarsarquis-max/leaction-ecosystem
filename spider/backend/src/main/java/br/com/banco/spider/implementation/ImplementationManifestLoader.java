package br.com.banco.spider.implementation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import jakarta.annotation.PostConstruct;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

@Component
public class ImplementationManifestLoader {

  public static final String MANIFEST_PATH = "implementation/spider-capability-manifest.json";
  public static final String SCHEMA_PATH = "implementation/spider-capability-manifest.schema.json";
  public static final String ROADMAP_CONTRACT_PATH =
      "implementation/spider-roadmap-015-026-contract.json";

  private final ObjectMapper mapper;
  private volatile SpiderImplementationManifest cached;

  public ImplementationManifestLoader(ObjectMapper mapper) {
    this.mapper = mapper;
  }

  @PostConstruct
  void warm() {
    cached = loadAndValidate();
  }

  public SpiderImplementationManifest getManifest() {
    SpiderImplementationManifest m = cached;
    if (m == null) {
      m = loadAndValidate();
      cached = m;
    }
    return m;
  }

  public SpiderImplementationManifest loadAndValidate() {
    try {
      JsonNode schemaNode = readTree(SCHEMA_PATH);
      JsonNode manifestNode = readTree(MANIFEST_PATH);
      JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012);
      JsonSchema schema = factory.getSchema(schemaNode);
      Set<ValidationMessage> errors = schema.validate(manifestNode);
      if (!errors.isEmpty()) {
        throw new IllegalStateException(
            "Capability manifest schema invalid: " + errors.iterator().next());
      }
      SpiderImplementationManifest manifest =
          mapper.treeToValue(manifestNode, SpiderImplementationManifest.class);
      validateBusinessRules(manifest);
      validateAgainstRoadmapContract(manifest);
      return manifest;
    } catch (IllegalStateException e) {
      throw e;
    } catch (Exception e) {
      throw new IllegalStateException("Failed to load capability manifest (fail-closed)", e);
    }
  }

  private void validateBusinessRules(SpiderImplementationManifest manifest) {
    List<String> problems = new ArrayList<>();
    if (!"GROUP_A_VISIBILITY_OBSERVABILITY".equals(manifest.currentGroup())) {
      problems.add("currentGroup must be GROUP_A_VISIBILITY_OBSERVABILITY");
    }
    if (!"SPIDER-PROMPT-016".equals(manifest.currentPrompt())) {
      problems.add("currentPrompt must be SPIDER-PROMPT-016");
    }
    for (ImplementationCapability c : manifest.capabilities()) {
      if ("PRODUCTION".equals(c.integrationLevel())) {
        problems.add(c.capabilityCode() + " must never be PRODUCTION");
      }
      if (c.promptRef() == null) {
        continue;
      }
      int n = Integer.parseInt(c.promptRef().substring("SPIDER-PROMPT-".length()));
      if (n <= 16 && !"VERIFIED".equals(c.status())) {
        problems.add(c.capabilityCode() + " expected VERIFIED");
      }
      if (n >= 17 && n <= 26 && !"PLANNED".equals(c.status())) {
        problems.add(c.capabilityCode() + " expected PLANNED");
      }
      if (n <= 16 && !"MOCK_ONLY".equals(c.integrationLevel())) {
        problems.add(c.capabilityCode() + " must be MOCK_ONLY while verified in Mock phase");
      }
      if (n == 25) {
        if (!"CORPORATE_SANDBOX".equals(c.integrationLevel())) {
          problems.add("CAP-025 must be CORPORATE_SANDBOX (planned)");
        }
        if (!"PLANNED".equals(c.status()) || !"NOT_IMPLEMENTED".equals(c.runtimeAvailability())) {
          problems.add("CAP-025 must remain planned/not-implemented (not active)");
        }
        if ("MOCK_ONLY".equals(c.integrationLevel())) {
          problems.add("CAP-025 must not be MOCK_ONLY");
        }
      }
      if (n == 26) {
        if (!"REAL_PILOT".equals(c.integrationLevel())) {
          problems.add("CAP-026 must be REAL_PILOT (planned)");
        }
        if ("PRODUCTION".equals(c.integrationLevel())) {
          problems.add("CAP-026 must never be PRODUCTION");
        }
      }
    }
    if (!problems.isEmpty()) {
      throw new IllegalStateException(
          "Capability manifest business rules failed: " + problems.getFirst());
    }
  }

  void validateAgainstRoadmapContract(SpiderImplementationManifest manifest) throws Exception {
    JsonNode contract = readTree(ROADMAP_CONTRACT_PATH);
    if (!manifest.currentGroup().equals(contract.path("currentGroup").asText())) {
      throw new IllegalStateException("Manifest currentGroup drifts from roadmap contract");
    }
    Map<String, ImplementationCapability> byPrompt =
        manifest.capabilities().stream()
            .filter(c -> c.promptRef() != null)
            .collect(
                Collectors.toMap(
                    ImplementationCapability::promptRef, Function.identity(), (a, b) -> a));
    for (JsonNode expected : contract.path("capabilities")) {
      String prompt = expected.path("promptRef").asText();
      ImplementationCapability actual = byPrompt.get(prompt);
      if (actual == null) {
        throw new IllegalStateException("Missing capability for " + prompt);
      }
      assertEq(prompt, "groupCode", expected.path("groupCode").asText(), actual.groupCode());
      assertEq(prompt, "title", expected.path("title").asText(), actual.title());
      assertEq(prompt, "status", expected.path("status").asText(), actual.status());
      assertEq(
          prompt,
          "runtimeAvailability",
          expected.path("runtimeAvailability").asText(),
          actual.runtimeAvailability());
      assertEq(
          prompt,
          "integrationLevel",
          expected.path("integrationLevel").asText(),
          actual.integrationLevel());
      List<String> expectedDeps = new ArrayList<>();
      expected.path("dependencies").forEach(n -> expectedDeps.add(n.asText()));
      if (!expectedDeps.equals(actual.dependencies())) {
        throw new IllegalStateException(
            prompt
                + " dependencies drift: expected "
                + expectedDeps
                + " actual "
                + actual.dependencies());
      }
      // objective present in contract — compare when non-blank
      String expectedObjective = expected.path("objective").asText(null);
      if (expectedObjective != null
          && !expectedObjective.isBlank()
          && !expectedObjective.equals(actual.objective())) {
        throw new IllegalStateException(prompt + " objective drifts from roadmap contract");
      }
    }
  }

  private static void assertEq(String prompt, String field, String expected, String actual) {
    if (!expected.equals(actual)) {
      throw new IllegalStateException(
          prompt + " " + field + " drifts: expected=" + expected + " actual=" + actual);
    }
  }

  private JsonNode readTree(String classpath) throws Exception {
    ClassPathResource res = new ClassPathResource(classpath);
    try (InputStream in = res.getInputStream()) {
      return mapper.readTree(in);
    }
  }
}
