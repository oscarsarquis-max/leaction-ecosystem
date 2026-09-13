package br.com.segsense.application.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class DemoProjectionJsonTest {

  @Test
  void roundTripsProjectionWithoutJackson() {
    Map<String, Object> projection = new LinkedHashMap<>();
    projection.put("id", "j1");
    projection.put("demoSliceOnly", true);
    projection.put("watermark", "DEMONSTRAÇÃO — SEM VALOR COMERCIAL");
    projection.put("items", List.of(Map.of("code", "STEP", "title", "Revisar", "notOfferable", true)));
    String json = DemoProjectionJson.write(projection);
    Map<String, Object> read = DemoProjectionJson.readObject(json);
    assertEquals("j1", read.get("id"));
    assertEquals(Boolean.TRUE, read.get("demoSliceOnly"));
    assertTrue(json.contains("SEM VALOR COMERCIAL"));
  }
}
