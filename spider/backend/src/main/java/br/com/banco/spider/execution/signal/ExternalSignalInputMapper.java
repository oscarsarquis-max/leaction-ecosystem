package br.com.banco.spider.execution.signal;

import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.stereotype.Component;

@Component
public class ExternalSignalInputMapper {

  private final ObjectMapper mapper = new ObjectMapper();

  public CanonicalPayload map(
      ExternalSignalInputMappingKind kind,
      ExternalSignalEnvelope envelope,
      ExecutionWaitRecord wait) {
    return switch (kind) {
      case STATUS_ONLY_V1 -> {
        ObjectNode n = mapper.createObjectNode();
        n.put("disposition", envelope.completion().disposition().name());
        yield CanonicalPayload.of(n);
      }
      case RESULT_DATA_V1 -> {
        JsonNode data =
            envelope.completion().outcome() != null
                ? envelope.completion().outcome().canonicalData()
                : mapper.createObjectNode();
        yield CanonicalPayload.of(data == null ? mapper.createObjectNode() : data);
      }
      case MERGE_WITH_WAIT_CONTEXT_V1 -> {
        ObjectNode n = mapper.createObjectNode();
        n.put("waitId", wait.waitId());
        n.put("executionId", wait.executionId());
        n.put("disposition", envelope.completion().disposition().name());
        if (envelope.completion().outcome() != null
            && envelope.completion().outcome().canonicalData() != null
            && envelope.completion().outcome().canonicalData().isObject()) {
          envelope
              .completion()
              .outcome()
              .canonicalData()
              .fields()
              .forEachRemaining(
                  e -> {
                    if (n.has(e.getKey())) {
                      throw new IllegalArgumentException("MERGE_CONFLICT:" + e.getKey());
                    }
                    n.set(e.getKey(), e.getValue());
                  });
        }
        yield CanonicalPayload.of(n);
      }
    };
  }
}
