package br.com.banco.spider.execution.signal;

import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.governance.GovernanceExecutionReference;
import br.com.banco.spider.governance.GovernedEffectType;
import br.com.banco.spider.governance.GovernedRuntimeSupport;
import br.com.banco.spider.governance.GovernanceContextException;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@Service
public class ExternalSignalIngressContextResolver {

  private static final Logger log =
      LoggerFactory.getLogger(ExternalSignalIngressContextResolver.class);

  private final ExecutionWaitStorePort waitStore;
  private final ObjectProvider<GovernedRuntimeSupport> governedRuntime;

  public ExternalSignalIngressContextResolver(
      ExecutionWaitStorePort waitStore, ObjectProvider<GovernedRuntimeSupport> governedRuntime) {
    this.waitStore = waitStore;
    this.governedRuntime = governedRuntime;
  }

  public Mono<Optional<ExternalSignalIngressContext>> resolveForWait(ExecutionWaitRecord wait) {
    GovernedRuntimeSupport support = governedRuntime.getIfAvailable();
    if (support == null) {
      return Mono.just(Optional.empty());
    }
    return support
        .resolveForExecution(wait.executionId(), GovernedEffectType.SIGNAL_APPLICATION)
        .map(resolved -> buildContext(wait, resolved))
        .onErrorResume(
            GovernanceContextException.class,
            ex -> {
              log.info(
                  "event=historical_ingress_context_failure reasonCode={}", ex.reasonCode());
              return Mono.just(Optional.empty());
            });
  }

  private Optional<ExternalSignalIngressContext> buildContext(
      ExecutionWaitRecord wait, GovernedRuntimeSupport.Resolved resolved) {
    if (resolved.blocksExternalEffect()) {
      log.info("event=historical_ingress_context_blocked reasonCode={}", resolved.decision());
      return Optional.empty();
    }
    if (resolved.context().isEmpty() || resolved.reference().isEmpty()) {
      return Optional.empty();
    }
    var ctx = resolved.context().get();
    GovernanceExecutionReference ref = resolved.reference().get();
    String defRef =
        wait.signalDefinitionRef() != null
            ? wait.signalDefinitionRef()
            : ctx.waitPolicyCatalog()
                .findByRef(wait.waitPolicyRef())
                .map(p -> p.signalDefinitionRef())
                .orElse(null);
    if (defRef == null || defRef.isBlank()) {
      return Optional.empty();
    }
    Optional<ExternalSignalIngressContext> built =
        ctx.externalSignalDefinitionCatalog()
            .findByExactRef(defRef)
            .filter(ExternalSignalDefinition::isEligible)
            .map(def -> ExternalSignalIngressContext.from(wait, ref, ctx, def));
    if (built.isPresent()) {
      log.info(
          "event=historical_ingress_context_loaded reasonCode=OK mode={}", ref.governanceMode());
    }
    return built;
  }

  public Mono<Optional<ExecutionWaitRecord>> findActiveWait(String executionId, String stepId) {
    return Mono.fromCallable(() -> waitStore.findActiveByExecutionAndStep(executionId, stepId))
        .subscribeOn(Schedulers.boundedElastic())
        .map(
            opt ->
                opt.filter(
                    w -> w.state() == WaitState.WAITING || w.state() == WaitState.RESUMING));
  }
}
