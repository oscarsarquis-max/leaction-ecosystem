package br.com.banco.spider.engine.mapper;

import java.util.HashMap;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Traduz payload contextual do canal para o contrato esperado pelo legado. */
@Component
public class ContextMapper {

  public Map<String, Object> toCadastroLookup(String customerExternalId, Map<String, Object> context) {
    Map<String, Object> out = new HashMap<>();
    out.put("customerExternalId", customerExternalId);
    if (context != null) {
      out.putAll(context);
    }
    return out;
  }

  public Map<String, Object> toCreditoAnalise(String customerExternalId, Map<String, Object> context) {
    Map<String, Object> out = new HashMap<>();
    out.put("customerExternalId", customerExternalId == null ? "" : customerExternalId);
    out.put("context", context == null ? Map.of() : context);
    return out;
  }
}
