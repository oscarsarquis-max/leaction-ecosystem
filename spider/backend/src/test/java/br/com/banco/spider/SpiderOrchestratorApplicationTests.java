package br.com.banco.spider;

import static org.junit.jupiter.api.Assertions.assertNotNull;

import br.com.banco.spider.engine.mapper.ContextMapper;
import java.util.Map;
import org.junit.jupiter.api.Test;

class SpiderOrchestratorApplicationTests {

  @Test
  void contextMapperBuildsCreditoPayload() {
    ContextMapper mapper = new ContextMapper();
    Map<String, Object> body = mapper.toCreditoAnalise("CLI-1", Map.of("canal", "teste"));
    assertNotNull(body.get("customerExternalId"));
    assertNotNull(body.get("context"));
  }
}
