package br.com.banco.spider.domain;

import java.util.List;
import java.util.Map;
import java.util.UUID;

public record OrchestrationResult(
    UUID correlationId,
    String productCode,
    String status,
    List<StepResult> steps,
    Map<String, Object> aggregated) {

  public record StepResult(String name, String system, String status, Map<String, Object> data) {}
}
