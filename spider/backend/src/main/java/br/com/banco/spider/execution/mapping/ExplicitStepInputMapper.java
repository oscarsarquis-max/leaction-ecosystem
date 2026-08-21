package br.com.banco.spider.execution.mapping;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Instant;
import java.util.Iterator;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ExplicitStepInputMapper implements StepInputMappingPort {

  private final ObjectMapper mapper;
  private final int maxDepth;
  private final int maxBytes;

  @org.springframework.beans.factory.annotation.Autowired
  public ExplicitStepInputMapper(
      ObjectMapper objectMapper,
      @Value("${spider.canonical.mapping.max-depth:8}") int maxDepth,
      @Value("${spider.canonical.mapping.max-bytes:65536}") int maxBytes) {
    this.mapper = objectMapper;
    this.maxDepth = maxDepth;
    this.maxBytes = maxBytes;
  }

  public ExplicitStepInputMapper(ObjectMapper objectMapper) {
    this(objectMapper, 8, 65536);
  }

  @Override
  public MappingResult map(MappingRequest request) {
    try {
      return switch (request.kind()) {
        case ROOT_REQUEST_CANONICAL_DATA -> {
          JsonNode data =
              request.rootCanonicalData() == null
                  ? mapper.nullNode()
                  : request.rootCanonicalData().deepCopy();
          validateSize(data);
          validateDepth(data, 0);
          yield MappingResult.ok(data);
        }
        case PREVIOUS_STEP_CANONICAL_DATA -> {
          if (request.previousStepCanonicalData() == null
              || request.previousStepCanonicalData().isNull()) {
            yield MappingResult.fail(
                error("MAPPING_PREVIOUS_MISSING", "Previous step canonicalData is required"));
          }
          JsonNode data = request.previousStepCanonicalData().deepCopy();
          validateSize(data);
          validateDepth(data, 0);
          yield MappingResult.ok(data);
        }
        case MERGE_ROOT_AND_PREVIOUS_CANONICAL_DATA -> {
          JsonNode merged = merge(request.rootCanonicalData(), request.previousStepCanonicalData());
          validateSize(merged);
          validateDepth(merged, 0);
          yield MappingResult.ok(merged);
        }
      };
    } catch (MappingException ex) {
      return MappingResult.fail(error(ex.code, ex.getMessage()));
    } catch (Exception ex) {
      return MappingResult.fail(error("MAPPING_FAILED", "Mapping failed"));
    }
  }

  private JsonNode merge(JsonNode root, JsonNode previous) {
    if (root == null || root.isNull()) {
      root = mapper.createObjectNode();
    }
    if (previous == null || previous.isNull()) {
      previous = mapper.createObjectNode();
    }
    if (!root.isObject() || !previous.isObject()) {
      throw new MappingException("MAPPING_MERGE_TYPE", "Merge requires object/maps on both sides");
    }
    ObjectNode out = mapper.createObjectNode();
    Iterator<Map.Entry<String, JsonNode>> rootFields = root.fields();
    while (rootFields.hasNext()) {
      Map.Entry<String, JsonNode> e = rootFields.next();
      out.set(e.getKey(), e.getValue().deepCopy());
    }
    Iterator<Map.Entry<String, JsonNode>> prevFields = previous.fields();
    while (prevFields.hasNext()) {
      Map.Entry<String, JsonNode> e = prevFields.next();
      if (out.has(e.getKey())) {
        throw new MappingException(
            "MAPPING_MERGE_CONFLICT", "Conflicting key in merge: " + e.getKey());
      }
      out.set(e.getKey(), e.getValue().deepCopy());
    }
    return out;
  }

  private void validateSize(JsonNode node) {
    try {
      int size = mapper.writeValueAsBytes(node == null ? mapper.nullNode() : node).length;
      if (size > maxBytes) {
        throw new MappingException("MAPPING_SIZE_LIMIT", "Mapped payload exceeds max-bytes");
      }
    } catch (MappingException e) {
      throw e;
    } catch (Exception e) {
      throw new MappingException("MAPPING_SIZE_LIMIT", "Unable to measure mapped payload");
    }
  }

  private void validateDepth(JsonNode node, int depth) {
    if (depth > maxDepth) {
      throw new MappingException("MAPPING_DEPTH_LIMIT", "Mapped payload exceeds max-depth");
    }
    if (node != null && node.isContainerNode()) {
      node.forEach(child -> validateDepth(child, depth + 1));
    }
  }

  private static CanonicalError error(String code, String message) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(ErrorCategory.CONTRACT)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("step_input_mapping", null, null, null))
        .build();
  }

  private static final class MappingException extends RuntimeException {
    final String code;

    MappingException(String code, String message) {
      super(message);
      this.code = code;
    }
  }
}
