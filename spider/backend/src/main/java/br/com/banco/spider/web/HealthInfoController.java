package br.com.banco.spider.web;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/v1")
@Tag(name = "Meta")
public class HealthInfoController {

  @GetMapping("/meta")
  @Operation(summary = "Metadados do orquestrador")
  public Mono<Map<String, Object>> meta() {
    return Mono.just(
        Map.of(
            "name", "spider-orchestrator",
            "role", "reactive-context-orchestrator",
            "version", "0.1.0",
            "stack", "webflux+jpa-tech-store"));
  }
}
