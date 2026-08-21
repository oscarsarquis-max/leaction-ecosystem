package br.com.banco.spider.governance;

import br.com.banco.spider.execution.callback.CallbackBindingResolverPort;
import br.com.banco.spider.execution.callback.CallbackDefinitionCatalogPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryPolicyCatalogPort;
import br.com.banco.spider.execution.callback.CallbackReconciliationPolicyCatalogPort;
import br.com.banco.spider.execution.callback.CallbackStatusQueryBindingResolver;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.retry.RetryPolicyCatalogPort;
import br.com.banco.spider.execution.wait.WaitPolicyCatalogPort;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import br.com.banco.spider.governance.port.HistoricalGovernanceContextLoader;
import br.com.banco.spider.integration.binding.AdapterBindingResolverPort;
import br.com.banco.spider.security.integrity.IntegrityProfileCatalogPort;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

/**
 * Resolve catálogos efetivos para execução existente: histórico em CONTROL_PLANE / fixation;
 * defaults injetados em STATIC sem fixation.
 */
@Service
public class GovernedRuntimeSupport {

  private static final Logger log = LoggerFactory.getLogger(GovernedRuntimeSupport.class);

  private final ObjectProvider<DefaultGovernanceResolutionContextProvider> modeProvider;
  private final ObjectProvider<HistoricalGovernanceContextLoader> loader;
  private final ObjectProvider<GovernanceInFlightDecisionService> decisions;
  private final ExecutionGovernanceFixationStorePort fixationStore;

  public GovernedRuntimeSupport(
      ObjectProvider<DefaultGovernanceResolutionContextProvider> modeProvider,
      ObjectProvider<HistoricalGovernanceContextLoader> loader,
      ObjectProvider<GovernanceInFlightDecisionService> decisions,
      ExecutionGovernanceFixationStorePort fixationStore) {
    this.modeProvider = modeProvider;
    this.loader = loader;
    this.decisions = decisions;
    this.fixationStore = fixationStore;
  }

  public record Resolved(
      Optional<GovernanceResolutionContext> context,
      Optional<GovernanceExecutionReference> reference,
      GovernanceInFlightDecision decision) {

    public RetryPolicyCatalogPort retryOr(RetryPolicyCatalogPort fallback) {
      return context.map(GovernanceResolutionContext::retryPolicyCatalog).orElse(fallback);
    }

    public AdapterBindingResolverPort bindingOr(AdapterBindingResolverPort fallback) {
      return context.map(GovernanceResolutionContext::adapterBindingResolver).orElse(fallback);
    }

    public WaitPolicyCatalogPort waitOr(WaitPolicyCatalogPort fallback) {
      return context.map(GovernanceResolutionContext::waitPolicyCatalog).orElse(fallback);
    }

    public CallbackDefinitionCatalogPort callbackDefOr(CallbackDefinitionCatalogPort fallback) {
      return context.map(GovernanceResolutionContext::callbackDefinitionCatalog).orElse(fallback);
    }

    public CallbackDeliveryPolicyCatalogPort deliveryOr(CallbackDeliveryPolicyCatalogPort fallback) {
      return context
          .map(GovernanceResolutionContext::callbackDeliveryPolicyCatalog)
          .orElse(fallback);
    }

    public CallbackReconciliationPolicyCatalogPort reconciliationOr(
        CallbackReconciliationPolicyCatalogPort fallback) {
      return context
          .map(GovernanceResolutionContext::callbackReconciliationPolicyCatalog)
          .orElse(fallback);
    }

    public CallbackBindingResolverPort callbackBindingOr(CallbackBindingResolverPort fallback) {
      return context.map(GovernanceResolutionContext::callbackBindingResolver).orElse(fallback);
    }

    public CallbackStatusQueryBindingResolver statusQueryOr(
        CallbackStatusQueryBindingResolver fallback) {
      return context.map(GovernanceResolutionContext::statusQueryBindingResolver).orElse(fallback);
    }

    public IntegrityProfileCatalogPort integrityOr(IntegrityProfileCatalogPort fallback) {
      return context.map(GovernanceResolutionContext::integrityProfileCatalog).orElse(fallback);
    }

    public boolean allowsExternalEffect() {
      return decision == GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT
          || decision == GovernanceInFlightDecision.ALLOW_NON_EFFECTING_STATE_TRANSITION;
    }

    public boolean blocksExternalEffect() {
      return decision == GovernanceInFlightDecision.STOP_BEFORE_EFFECT
          || decision == GovernanceInFlightDecision.REQUIRE_MANUAL_REVIEW;
    }
  }

  public Mono<Resolved> resolveForExecution(String executionId, GovernedEffectType effect) {
    return resolveForExecution(executionId, effect, null);
  }

  public Mono<Resolved> resolveForExecution(
      String executionId, GovernedEffectType effect, ExecutionState state) {
    DefaultGovernanceResolutionContextProvider mode = modeProvider.getIfAvailable();
    HistoricalGovernanceContextLoader hist = loader.getIfAvailable();
    GovernanceInFlightDecisionService dec = decisions.getIfAvailable();
    boolean controlPlane = mode != null && mode.isControlPlaneActive();

    return Mono.fromCallable(() -> fixationStore.findByExecutionId(executionId))
        .subscribeOn(Schedulers.boundedElastic())
        .flatMap(
            fixOpt -> {
              if (fixOpt.isEmpty()) {
                if (controlPlane) {
                  log.info(
                      "event=historical_context_load_failure reasonCode=GOVERNANCE_FIXATION_NOT_FOUND");
                  return Mono.error(
                      GovernanceContextException.of("GOVERNANCE_FIXATION_NOT_FOUND"));
                }
                return Mono.just(
                    new Resolved(
                        Optional.empty(),
                        Optional.empty(),
                        GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT));
              }
              if (hist == null) {
                if (controlPlane) {
                  return Mono.error(
                      GovernanceContextException.of("GOVERNANCE_CONTEXT_INCOMPATIBLE"));
                }
                return Mono.just(
                    new Resolved(
                        Optional.empty(),
                        Optional.of(GovernanceExecutionReference.from(fixOpt.get())),
                        GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT));
              }
              ExecutionGovernanceFixation fixation = fixOpt.get();
              GovernanceExecutionReference ref = GovernanceExecutionReference.from(fixation);
              GovernanceInFlightDecision decision =
                  dec == null
                      ? GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT
                      : dec.decide(ref, effect, state);
              if (decision == GovernanceInFlightDecision.STOP_BEFORE_EFFECT
                  || decision == GovernanceInFlightDecision.REQUIRE_MANUAL_REVIEW) {
                log.info(
                    "event=adapter_prevented_before_effect reasonCode={} effectType={}",
                    decision,
                    effect);
                return Mono.just(new Resolved(Optional.empty(), Optional.of(ref), decision));
              }
              return hist.loadForExecution(executionId)
                  .map(ctx -> new Resolved(Optional.of(ctx), Optional.of(ref), decision))
                  .doOnNext(
                      r ->
                          log.info(
                              "event=resume_using_fixed_snapshot reasonCode=HISTORICAL mode={}",
                              fixation.governanceMode()));
            });
  }
}
