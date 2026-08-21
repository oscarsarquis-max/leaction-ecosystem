package br.com.banco.spider.execution.mapping;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;

class ExplicitStepInputMapperTest {

  private final ExplicitStepInputMapper mapper = new ExplicitStepInputMapper(new ObjectMapper());
  private final ObjectMapper om = new ObjectMapper();

  @Test
  void rootRequest() {
    ObjectNode root = om.createObjectNode().put("a", 1);
    var r =
        mapper.map(
            new StepInputMappingPort.MappingRequest(
                StepInputMappingKind.ROOT_REQUEST_CANONICAL_DATA, root, null));
    assertTrue(r.success());
    assertTrue(r.canonicalData().has("a"));
  }

  @Test
  void previousMissingFails() {
    var r =
        mapper.map(
            new StepInputMappingPort.MappingRequest(
                StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA, null, null));
    assertFalse(r.success());
  }

  @Test
  void mergeWithoutConflict() {
    ObjectNode root = om.createObjectNode().put("a", 1);
    ObjectNode prev = om.createObjectNode().put("b", 2);
    var r =
        mapper.map(
            new StepInputMappingPort.MappingRequest(
                StepInputMappingKind.MERGE_ROOT_AND_PREVIOUS_CANONICAL_DATA, root, prev));
    assertTrue(r.success());
    assertTrue(r.canonicalData().has("a") && r.canonicalData().has("b"));
  }

  @Test
  void mergeConflictRejected() {
    ObjectNode root = om.createObjectNode().put("a", 1);
    ObjectNode prev = om.createObjectNode().put("a", 2);
    var r =
        mapper.map(
            new StepInputMappingPort.MappingRequest(
                StepInputMappingKind.MERGE_ROOT_AND_PREVIOUS_CANONICAL_DATA, root, prev));
    assertFalse(r.success());
    assertTrue(r.error().code().contains("CONFLICT"));
  }

  @Test
  void rootImmutable() {
    ObjectNode root = om.createObjectNode().put("a", 1);
    var r =
        mapper.map(
            new StepInputMappingPort.MappingRequest(
                StepInputMappingKind.ROOT_REQUEST_CANONICAL_DATA, root, null));
    ((ObjectNode) r.canonicalData()).put("a", 99);
    assertTrue(root.get("a").asInt() == 1);
  }
}
