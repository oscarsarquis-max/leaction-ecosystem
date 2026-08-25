package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.config.CapacityProperties;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.workers.WorkerBacklogQueryService;
import br.com.banco.spider.operational.workers.WorkerBacklogStatus;
import br.com.banco.spider.operational.workers.WorkerBacklogView;
import br.com.banco.spider.operational.workers.WorkerType;
import java.time.Instant;
import java.util.Optional;
import org.springframework.beans.factory.ObjectProvider;

/**
 * Admissão governada. Decide antes de qualquer efeito: em modo observação o desfecho pretendido é
 * registrado mas o trabalho segue, e em modo aplicado a recusa acontece cedo o bastante para não
 * consumir nada do runtime.
 *
 * <p>A reserva de concorrência <em>não</em> acontece aqui: a avaliação apenas observa a ocupação do
 * bulkhead. Quem reserva é o chamador, imediatamente antes de trabalhar e com liberação garantida em
 * {@code finally} — só assim uma decisão avaliada e depois descartada não vaza uma vaga.
 */
public class CapacityAdmissionService {

  private final CapacityProperties properties;
  private final CapacityPolicyCatalog catalog;
  private final BulkheadService bulkheads;
  private final CircuitBreakerService circuits;
  private final QuotaService quotas;
  private final CapacityDecisionStore decisions;
  private final CapacityTelemetry telemetry;
  private final SpiderClock clock;
  private final IdentifierGenerator ids;
  private final ObjectProvider<WorkerBacklogQueryService> backlogProvider;

  public CapacityAdmissionService(
      CapacityProperties properties,
      CapacityPolicyCatalog catalog,
      BulkheadService bulkheads,
      CircuitBreakerService circuits,
      QuotaService quotas,
      CapacityDecisionStore decisions,
      CapacityTelemetry telemetry,
      SpiderClock clock,
      IdentifierGenerator ids,
      ObjectProvider<WorkerBacklogQueryService> backlogProvider) {
    this.properties = properties;
    this.catalog = catalog;
    this.bulkheads = bulkheads;
    this.circuits = circuits;
    this.quotas = quotas;
    this.decisions = decisions;
    this.telemetry = telemetry;
    this.clock = clock;
    this.ids = ids;
    this.backlogProvider = backlogProvider;
  }

  public CapacityMode mode() {
    if (!properties.isEnabled()) {
      return CapacityMode.DISABLED;
    }
    return properties.getEnforcement().isEnabled()
        ? CapacityMode.ENFORCED
        : CapacityMode.MONITOR_ONLY;
  }

  public AdmissionDecision evaluate(AdmissionRequest request) {
    if (!properties.isEnabled()) {
      return bypass(request, AdmissionDecision.MONITOR_BYPASS);
    }
    Optional<CapacityPolicy> policy = catalog.resolve(request);
    if (policy.isEmpty()) {
      return record(bypass(request, AdmissionDecision.NO_POLICY_MATCH));
    }
    return evaluate(request, policy.get());
  }

  /**
   * Avaliação contra uma política explícita. Usada pelo laboratório de falhas para demonstrar cada
   * proteção em um escopo dedicado, sem tocar nas políticas publicadas.
   */
  public AdmissionDecision evaluate(AdmissionRequest request, CapacityPolicy policy) {
    if (!properties.isEnabled()) {
      return bypass(request, AdmissionDecision.MONITOR_BYPASS);
    }
    if (policy.state() == CapacityPolicyState.DISABLED) {
      return record(decision(request, policy, AdmissionResult.ADMITTED,
          AdmissionDecision.POLICY_DISABLED, null, true));
    }
    String scopeKey = policy.scopeKey();
    bulkheads.register(scopeKey, policy.limits().maxConcurrency());
    boolean enforcing = enforcing(policy);
    Intent intent = intended(request, policy, scopeKey, enforcing);

    if (!enforcing) {
      String reasonCode =
          intent.result() == AdmissionResult.ADMITTED
              ? AdmissionDecision.ADMITTED
              : AdmissionDecision.MONITOR_ONLY_PREFIX + intent.result().name();
      return record(
          decision(request, policy, AdmissionResult.ADMITTED, reasonCode, intent.shedReason(), true));
    }
    return record(
        decision(request, policy, intent.result(), intent.reasonCode(), intent.shedReason(), false));
  }

  /**
   * Registra o descarte de um trabalho que havia sido admitido — o caso em que a vaga de concorrência
   * desapareceu entre a decisão e a reserva.
   */
  public AdmissionDecision recordShed(AdmissionDecision admitted, ShedReason reason) {
    AdmissionDecision shed =
        new AdmissionDecision(
            ids.nextId("capdec"),
            admitted.requestedAt(),
            clock.now(),
            AdmissionResult.SHED,
            reason.name(),
            admitted.policyRef(),
            admitted.policyVersion(),
            admitted.scopeType(),
            admitted.scopeRef(),
            reason,
            false,
            admitted.correlationRef());
    decisions.record(shed);
    telemetry.emitDecision(shed);
    telemetry.emitShed(shed, reason);
    return shed;
  }

  /** Alimenta o disjuntor do escopo com o desfecho técnico observado no ciclo. */
  public void recordOutcome(AdmissionDecision decision, boolean technicalFailure) {
    if (decision == null || decision.policyRef() == null) {
      return;
    }
    Optional<CapacityPolicy> policy = catalog.findByRef(decision.policyRef());
    if (policy.isEmpty()) {
      return;
    }
    if (technicalFailure) {
      circuits.recordFailure(decision.scopeKey(), policy.get());
    } else {
      circuits.recordSuccess(decision.scopeKey(), policy.get());
    }
  }

  public void recordOutcome(AdmissionDecision decision, CapacityPolicy policy, boolean failure) {
    if (decision == null || policy == null) {
      return;
    }
    if (failure) {
      circuits.recordFailure(decision.scopeKey(), policy);
    } else {
      circuits.recordSuccess(decision.scopeKey(), policy);
    }
  }

  public BulkheadService bulkheads() {
    return bulkheads;
  }

  public CircuitBreakerService circuits() {
    return circuits;
  }

  public QuotaService quotas() {
    return quotas;
  }

  private boolean enforcing(CapacityPolicy policy) {
    return properties.getEnforcement().isEnabled()
        && policy.state() == CapacityPolicyState.ACTIVE
        && policy.enforced();
  }

  /**
   * Ordem deliberada: disjuntor, concorrência, quota e por último backlog. A verificação mais barata
   * e mais informativa vem primeiro, e o backlog — que depende de consulta às fontes canônicas — só é
   * consultado quando o pedido já passou por tudo o mais.
   */
  private Intent intended(
      AdmissionRequest request, CapacityPolicy policy, String scopeKey, boolean enforcing) {
    if (!circuits.allowRequest(scopeKey, policy)) {
      return new Intent(
          AdmissionResult.REJECTED_CIRCUIT_OPEN, "CIRCUIT_OPEN", ShedReason.CIRCUIT_OPEN);
    }
    if (bulkheads.saturated(scopeKey, policy.limits().maxConcurrency())) {
      telemetry.emitBulkheadSaturated(scopeKey, policy.ref());
      return new Intent(
          AdmissionResult.REJECTED_CAPACITY,
          ShedReason.CONCURRENCY_EXHAUSTED.name(),
          ShedReason.CONCURRENCY_EXHAUSTED);
    }
    if (policy.limits().limitsQuota()
        && !quotas.tryConsume(
            scopeKey, policy.limits().quotaPerWindow(), policy.limits().window())) {
      telemetry.emitQuotaExhausted(scopeKey, policy.ref());
      return new Intent(
          AdmissionResult.REJECTED_QUOTA,
          ShedReason.QUOTA_EXHAUSTED.name(),
          ShedReason.QUOTA_EXHAUSTED);
    }
    return backlogIntent(request, policy);
  }

  private Intent backlogIntent(AdmissionRequest request, CapacityPolicy policy) {
    if (!policy.limits().limitsHardBacklog() && !policy.limits().limitsSoftBacklog()) {
      return Intent.admitted();
    }
    Optional<WorkerBacklogView> backlog = backlog(request);
    if (backlog.isEmpty() || backlog.get().status() == WorkerBacklogStatus.UNKNOWN) {
      return Intent.admitted();
    }
    int pending = backlog.get().eligibleCount();
    if (policy.limits().limitsHardBacklog() && pending >= policy.limits().hardBacklogLimit()) {
      return new Intent(
          AdmissionResult.SHED,
          ShedReason.BACKLOG_HARD_LIMIT.name(),
          ShedReason.BACKLOG_HARD_LIMIT);
    }
    if (policy.limits().limitsSoftBacklog() && pending >= policy.limits().softBacklogLimit()) {
      return new Intent(AdmissionResult.DELAYED, "SOFT_BACKLOG_LIMIT", null);
    }
    return Intent.admitted();
  }

  private Optional<WorkerBacklogView> backlog(AdmissionRequest request) {
    WorkerBacklogQueryService service = backlogProvider.getIfAvailable();
    if (service == null || request.workerType() == null) {
      return Optional.empty();
    }
    try {
      return Optional.of(service.backlog(WorkerType.valueOf(request.workerType())));
    } catch (RuntimeException unavailable) {
      return Optional.empty();
    }
  }

  private AdmissionDecision bypass(AdmissionRequest request, String reasonCode) {
    Instant now = clock.now();
    return new AdmissionDecision(
        ids.nextId("capdec"),
        request.requestedAt(),
        now,
        AdmissionResult.ADMITTED,
        reasonCode,
        null,
        null,
        request.scopeType(),
        request.scopeRef(),
        null,
        true,
        request.correlationRef());
  }

  private AdmissionDecision decision(
      AdmissionRequest request,
      CapacityPolicy policy,
      AdmissionResult result,
      String reasonCode,
      ShedReason shedReason,
      boolean monitorOnly) {
    return new AdmissionDecision(
        ids.nextId("capdec"),
        request.requestedAt(),
        clock.now(),
        result,
        reasonCode,
        policy.ref(),
        policy.version(),
        policy.scopeType(),
        policy.scopeRef(),
        shedReason,
        monitorOnly,
        request.correlationRef());
  }

  private AdmissionDecision record(AdmissionDecision decision) {
    decisions.record(decision);
    telemetry.emitDecision(decision);
    return decision;
  }

  private record Intent(AdmissionResult result, String reasonCode, ShedReason shedReason) {
    static Intent admitted() {
      return new Intent(AdmissionResult.ADMITTED, AdmissionDecision.ADMITTED, null);
    }
  }
}
