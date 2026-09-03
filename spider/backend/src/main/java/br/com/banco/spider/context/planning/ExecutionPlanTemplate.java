package br.com.banco.spider.context.planning;

import java.util.List;

public record ExecutionPlanTemplate(
    String planType, String intent, List<ContextExecutionPlanStep> steps) {

  public ExecutionPlanTemplate {
    steps = List.copyOf(steps);
  }
}
