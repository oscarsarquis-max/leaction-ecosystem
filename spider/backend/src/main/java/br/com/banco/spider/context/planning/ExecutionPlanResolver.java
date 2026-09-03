package br.com.banco.spider.context.planning;

import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import java.util.Optional;

public interface ExecutionPlanResolver {
  Optional<ContextExecutionPlan> resolve(
      IntentContract contract, ContextPolicyGuard.GuardResult guard);
}
