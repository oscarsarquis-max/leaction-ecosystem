package br.com.banco.spider.context.planning;

import java.util.List;
import java.util.Optional;

public interface ExecutionPlanCatalog {
  List<ExecutionPlanTemplate> list();

  Optional<ExecutionPlanTemplate> findByIntent(String intent);
}
