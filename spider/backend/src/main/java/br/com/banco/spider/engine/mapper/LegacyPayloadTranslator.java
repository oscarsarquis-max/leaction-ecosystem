package br.com.banco.spider.engine.mapper;

import br.com.banco.spider.domain.ProductOrchestrateRequest;
import java.util.HashMap;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Traduz a intenção de produto do originador para o contrato do legado financeiro. */
@Component
public class LegacyPayloadTranslator {

  public Map<String, Object> toLegadoRequest(ProductOrchestrateRequest request, String traceparent) {
    Map<String, Object> body = new HashMap<>();
    body.put("productId", request.productId());
    body.put("transactionId", request.transactionId());
    body.put("traceparent", traceparent);
    body.put("payload", request.payload() == null ? Map.of() : request.payload());
    body.put("channel", "spider-orchestrator");
    return body;
  }
}
