package br.com.spiderbank.inbound.http;

import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

  @GetMapping("/api/health")
  public Map<String, Object> health() {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("status", "UP");
    body.put("satelliteId", "spiderbank");
    body.put("role", "EXPERIENCE");
    body.put("purpose", "WORKING_CAPITAL_ASSESSMENT");
    body.put("environment", "MOCK_ONLY");
    return body;
  }
}
