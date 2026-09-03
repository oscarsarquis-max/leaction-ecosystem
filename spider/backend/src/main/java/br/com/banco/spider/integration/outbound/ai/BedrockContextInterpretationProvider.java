package br.com.banco.spider.integration.outbound.ai;

import br.com.banco.spider.context.application.ContextInterpreterPrompt;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider;
import br.com.banco.spider.context.application.port.InvalidContextInterpretationResponseException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import reactor.core.publisher.Mono;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelRequest;

/** Adapter AWS Bedrock/Anthropic. Tipos do provider ficam restritos a esta borda. */
public final class BedrockContextInterpretationProvider
    implements ContextInterpretationProvider {

  private static final Set<String> STRUCTURED_FIELDS =
      Set.of("status", "intent", "entities", "candidateIntents", "confidence");

  private final BedrockRuntimeAsyncClient client;
  private final ObjectMapper mapper;
  private final ContextInterpreterPrompt prompt;
  private final String modelId;

  public BedrockContextInterpretationProvider(
      BedrockRuntimeAsyncClient client,
      ObjectMapper mapper,
      ContextInterpreterPrompt prompt,
      String modelId) {
    this.client = client;
    this.mapper = mapper;
    this.prompt = prompt;
    this.modelId = modelId;
  }

  @Override
  public String providerId() {
    return "aws-bedrock-anthropic";
  }

  @Override
  public String modelId() {
    return modelId;
  }

  @Override
  public Mono<ProviderResult> interpret(ProviderRequest request) {
    long started = System.nanoTime();
    InvokeModelRequest invoke =
        InvokeModelRequest.builder()
            .modelId(modelId)
            .contentType("application/json")
            .accept("application/json")
            .body(SdkBytes.fromUtf8String(requestBody(request)))
            .build();
    return Mono.fromFuture(client.invokeModel(invoke))
        .map(
            response ->
                parseResponse(
                    response.body().asString(StandardCharsets.UTF_8),
                    Math.max(0, (System.nanoTime() - started) / 1_000_000)));
  }

  private String requestBody(ProviderRequest request) {
    try {
      ObjectNode root = mapper.createObjectNode();
      root.put("anthropic_version", "bedrock-2023-05-31");
      root.put("max_tokens", 700);
      root.put("temperature", 0);
      root.put("system", prompt.text());

      ObjectNode input = mapper.createObjectNode();
      input.put("objectiveText", request.objectiveText());
      input.put("promptVersion", request.promptVersion());
      input.put("contractSchemaVersion", request.contractSchemaVersion());
      input.set("allowedIntents", mapper.valueToTree(request.allowedIntents()));

      ObjectNode content = mapper.createObjectNode();
      content.put("type", "text");
      content.put("text", mapper.writeValueAsString(input));
      ObjectNode message = mapper.createObjectNode();
      message.put("role", "user");
      message.set("content", mapper.createArrayNode().add(content));
      root.set("messages", mapper.createArrayNode().add(message));
      return mapper.writeValueAsString(root);
    } catch (Exception error) {
      throw new InvalidContextInterpretationResponseException(
          "BEDROCK_REQUEST_SERIALIZATION_FAILED", error);
    }
  }

  private ProviderResult parseResponse(String body, long latencyMs) {
    try {
      JsonNode envelope = mapper.readTree(body);
      JsonNode content = envelope.path("content");
      if (!content.isArray() || content.isEmpty()) {
        throw new InvalidContextInterpretationResponseException("BEDROCK_CONTENT_MISSING");
      }
      String structured = content.get(0).path("text").textValue();
      if (structured == null) {
        throw new InvalidContextInterpretationResponseException(
            "BEDROCK_STRUCTURED_TEXT_MISSING");
      }
      JsonNode result = mapper.readTree(structured);
      if (!result.isObject()) {
        throw new InvalidContextInterpretationResponseException(
            "BEDROCK_STRUCTURED_OBJECT_REQUIRED");
      }
      result
          .fieldNames()
          .forEachRemaining(
              field -> {
                if (!STRUCTURED_FIELDS.contains(field)) {
                  throw new InvalidContextInterpretationResponseException(
                      "BEDROCK_STRUCTURED_FIELD_NOT_ALLOWED");
                }
              });

      ProviderStatus status = ProviderStatus.valueOf(requiredText(result, "status"));
      String intent = nullableText(result.get("intent"));
      Map<String, String> entities = stringMap(result.path("entities"));
      List<String> candidates = stringList(result.path("candidateIntents"));
      JsonNode confidenceNode = result.get("confidence");
      if (confidenceNode == null || !confidenceNode.isNumber()) {
        throw new InvalidContextInterpretationResponseException(
            "BEDROCK_CONFIDENCE_INVALID");
      }
      BigDecimal confidence = confidenceNode.decimalValue();
      JsonNode usageNode = envelope.path("usage");
      Integer inputTokens = nullableInteger(usageNode.get("input_tokens"));
      Integer outputTokens = nullableInteger(usageNode.get("output_tokens"));
      Integer totalTokens =
          inputTokens == null || outputTokens == null ? null : inputTokens + outputTokens;
      return new ProviderResult(
          status,
          intent,
          entities,
          candidates,
          confidence,
          new Usage(inputTokens, outputTokens, totalTokens),
          latencyMs);
    } catch (InvalidContextInterpretationResponseException error) {
      throw error;
    } catch (Exception error) {
      throw new InvalidContextInterpretationResponseException(
          "BEDROCK_RESPONSE_INVALID", error);
    }
  }

  private static String requiredText(JsonNode object, String key) {
    String value = nullableText(object.get(key));
    if (value == null || value.isBlank()) {
      throw new InvalidContextInterpretationResponseException(
          "BEDROCK_" + key.toUpperCase() + "_MISSING");
    }
    return value;
  }

  private static String nullableText(JsonNode node) {
    return node == null || node.isNull() || !node.isTextual() ? null : node.textValue();
  }

  private static Integer nullableInteger(JsonNode node) {
    return node == null || !node.canConvertToInt() ? null : node.intValue();
  }

  private static Map<String, String> stringMap(JsonNode node) {
    if (!node.isObject()) {
      throw new InvalidContextInterpretationResponseException("BEDROCK_ENTITIES_INVALID");
    }
    Map<String, String> values = new LinkedHashMap<>();
    node.fields()
        .forEachRemaining(
            entry -> {
              if (!entry.getValue().isTextual()) {
                throw new InvalidContextInterpretationResponseException(
                    "BEDROCK_ENTITY_VALUE_INVALID");
              }
              values.put(entry.getKey(), entry.getValue().textValue());
            });
    return values;
  }

  private static List<String> stringList(JsonNode node) {
    if (!node.isArray()) {
      throw new InvalidContextInterpretationResponseException(
          "BEDROCK_CANDIDATES_INVALID");
    }
    List<String> values = new ArrayList<>();
    for (JsonNode item : (ArrayNode) node) {
      if (!item.isTextual()) {
        throw new InvalidContextInterpretationResponseException(
            "BEDROCK_CANDIDATE_INVALID");
      }
      values.add(item.textValue());
    }
    return values;
  }

}
