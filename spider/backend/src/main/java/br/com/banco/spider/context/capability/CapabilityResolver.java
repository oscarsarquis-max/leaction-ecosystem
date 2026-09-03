package br.com.banco.spider.context.capability;

import br.com.banco.spider.context.planning.ContextExecutionPlan;
import java.util.List;

public interface CapabilityResolver {
  List<CapabilityResolution> resolve(ContextExecutionPlan plan);
}
