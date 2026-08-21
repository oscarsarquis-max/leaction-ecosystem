package br.com.banco.spider.integration.mapping;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.ContextReference;
import br.com.banco.spider.canonical.contract.ContractDescriptor;
import br.com.banco.spider.canonical.contract.ExecutionIdentity;
import br.com.banco.spider.canonical.contract.ExecutionPolicyReference;
import br.com.banco.spider.canonical.contract.OriginDescriptor;
import br.com.banco.spider.canonical.contract.TargetDescriptor;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.canonical.versioning.VersionedReference;
import br.com.banco.spider.domain.ProductOrchestrateRequest;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Instant;
import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * Converte o DTO legado {@link ProductOrchestrateRequest} em envelope canônico mínimo.
 * Não conecta legado; apenas projeta referências opacas a partir dos campos atuais.
 */
@Component
public class ProductOrchestrateCanonicalMapper {

  public static final String SCHEMA_VERSION = "1.0";
  public static final String CONTRACT_VERSION = "1.0.0";

  private final ObjectMapper objectMapper;

  public ProductOrchestrateCanonicalMapper(ObjectMapper objectMapper) {
    this.objectMapper = objectMapper;
  }

  public CanonicalExecutionRequest toCanonical(
      ProductOrchestrateRequest request, String traceparent) {
    String executionId = "exec-" + UUID.randomUUID();
    String correlationId = "corr-" + request.transactionId();
    String tp =
        (traceparent == null || traceparent.isBlank())
            ? defaultTraceparent()
            : traceparent.trim();

    ObjectNode data = objectMapper.createObjectNode();
    data.put("productId", request.productId());
    data.put("transactionId", request.transactionId());
    if (request.payload() != null) {
      data.set("legacyPayloadProjection", objectMapper.valueToTree(request.payload()));
    }

    return CanonicalExecutionRequest.builder()
        .contract(new ContractDescriptor(SCHEMA_VERSION, CONTRACT_VERSION))
        .execution(
            new ExecutionIdentity(
                executionId,
                Instant.now(),
                "originator:" + request.productId() + ":" + request.transactionId()))
        .contextRef(
            new ContextReference(
                "ctx-" + request.transactionId(),
                "INTENT_PRODUCT_ORCHESTRATE@1.0.0",
                "CAP_LEGACY_BASELINE_ORCHESTRATE@1.0.0",
                request.productId() + "@1.0.0",
                "JOURNEY_LEGACY_BASELINE@1.0.0"))
        .origin(new OriginDescriptor("LEGACY_BASELINE_CHANNEL", "service-originador", null))
        .trace(new TraceDescriptor(correlationId, tp, null))
        .target(new TargetDescriptor("LEGACY_BASELINE_PROCESS", "orchestrate"))
        .payload(CanonicalPayload.of(data))
        .executionPolicy(ExecutionPolicyReference.empty())
        .callbackRef(VersionedReference.of("callback:originator-default", "1.0.0"))
        .build();
  }

  private static String defaultTraceparent() {
    String traceId = UUID.randomUUID().toString().replace("-", "");
    String spanId = UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    return "00-" + traceId + "-" + spanId + "-01";
  }

  public JsonNode asTree(CanonicalExecutionRequest request) {
    return objectMapper.valueToTree(request);
  }
}
