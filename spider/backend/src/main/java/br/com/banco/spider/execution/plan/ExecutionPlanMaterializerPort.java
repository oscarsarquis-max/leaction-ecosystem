package br.com.banco.spider.execution.plan;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.execution.route.RouteResolution;

public interface ExecutionPlanMaterializerPort {
  ExecutionPlanMaterialization materialize(
      CanonicalExecutionRequest request, RouteResolution resolution);
}
