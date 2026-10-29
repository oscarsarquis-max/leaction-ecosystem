package br.com.banco.spider.config;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class SandboxTelemetryEnabledTest {

  @Test
  void sandboxYamlEnablesTelemetrySoMonitorCanStoreSatelliteEvents() throws Exception {
    Path yaml = Path.of("src/main/resources/application-sandbox.yml");
    String text = Files.readString(yaml, StandardCharsets.UTF_8);
    int idx = text.indexOf("\n  telemetry:");
    assertTrue(idx >= 0, "sandbox profile must declare telemetry");
    String block = text.substring(idx, Math.min(text.length(), idx + 160));
    assertTrue(
        block.contains("SPIDER_TELEMETRY_ENABLED:true"),
        "sandbox telemetry must default on; otherwise READY satellite calls leave the Monitor empty");
  }
}
