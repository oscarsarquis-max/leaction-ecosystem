package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.workers.WorkerBacklogQueryService;
import br.com.banco.spider.operational.workers.WorkerBacklogStatus;
import br.com.banco.spider.operational.workers.WorkerBacklogView;
import br.com.banco.spider.operational.workers.WorkerType;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.springframework.beans.factory.ObjectProvider;

/**
 * Consolida a pressão por escopo publicado. Sem fonte de backlog o nível fica {@link
 * CapacityPressureLevel#UNKNOWN} — a leitura nunca afirma folga que não pôde observar.
 */
public class CapacityPressureService {

  private final CapacityPolicyCatalog catalog;
  private final BulkheadService bulkheads;
  private final CircuitBreakerService circuits;
  private final QuotaService quotas;
  private final SpiderClock clock;
  private final ObjectProvider<WorkerBacklogQueryService> backlogProvider;

  public CapacityPressureService(
      CapacityPolicyCatalog catalog,
      BulkheadService bulkheads,
      CircuitBreakerService circuits,
      QuotaService quotas,
      SpiderClock clock,
      ObjectProvider<WorkerBacklogQueryService> backlogProvider) {
    this.catalog = catalog;
    this.bulkheads = bulkheads;
    this.circuits = circuits;
    this.quotas = quotas;
    this.clock = clock;
    this.backlogProvider = backlogProvider;
  }

  public List<PressureSnapshot> pressure() {
    List<PressureSnapshot> snapshots = new ArrayList<>();
    for (CapacityPolicy policy : catalog.policies()) {
      snapshots.add(pressure(policy));
    }
    return List.copyOf(snapshots);
  }

  private PressureSnapshot pressure(CapacityPolicy policy) {
    String scopeKey = policy.scopeKey();
    CapacityLimit limits = policy.limits();
    int capacity = limits.maxConcurrency();
    int occupied = bulkheads.occupied(scopeKey);
    int utilization = capacity <= 0 ? 0 : Math.min(100, occupied * 100 / capacity);
    CircuitPhase phase = circuits.phase(scopeKey);
    int quotaUsed = limits.limitsQuota() ? quotas.used(scopeKey, limits.window()) : 0;
    Optional<WorkerBacklogView> backlog = backlog(policy);
    boolean backlogKnown =
        backlog.isPresent() && backlog.get().status() != WorkerBacklogStatus.UNKNOWN;
    int pending = backlogKnown ? backlog.get().eligibleCount() : 0;

    CapacityPressureLevel level = level(policy, utilization, quotaUsed, pending, phase, backlogKnown);
    return new PressureSnapshot(
        PressureSnapshot.SCHEMA_VERSION,
        scopeKey,
        policy.scopeType(),
        policy.scopeRef(),
        policy.ref(),
        level,
        occupied,
        capacity,
        utilization,
        pending,
        limits.softBacklogLimit(),
        limits.hardBacklogLimit(),
        quotaUsed,
        limits.quotaPerWindow(),
        phase,
        clock.now(),
        explain(level, backlogKnown));
  }

  private CapacityPressureLevel level(
      CapacityPolicy policy,
      int utilization,
      int quotaUsed,
      int pending,
      CircuitPhase phase,
      boolean backlogKnown) {
    CapacityLimit limits = policy.limits();
    if (phase == CircuitPhase.OPEN) {
      return CapacityPressureLevel.CRITICAL;
    }
    if (limits.limitsHardBacklog() && backlogKnown && pending >= limits.hardBacklogLimit()) {
      return CapacityPressureLevel.CRITICAL;
    }
    if (limits.limitsConcurrency() && utilization >= 100) {
      return CapacityPressureLevel.CRITICAL;
    }
    if (limits.limitsQuota() && quotaUsed >= limits.quotaPerWindow()) {
      return CapacityPressureLevel.HIGH;
    }
    if (limits.limitsSoftBacklog() && backlogKnown && pending >= limits.softBacklogLimit()) {
      return CapacityPressureLevel.HIGH;
    }
    if (phase == CircuitPhase.HALF_OPEN) {
      return CapacityPressureLevel.ELEVATED;
    }
    if (limits.limitsConcurrency() && utilization >= 75) {
      return CapacityPressureLevel.ELEVATED;
    }
    if (!backlogKnown && (limits.limitsHardBacklog() || limits.limitsSoftBacklog())) {
      return CapacityPressureLevel.UNKNOWN;
    }
    return CapacityPressureLevel.NORMAL;
  }

  private static String explain(CapacityPressureLevel level, boolean backlogKnown) {
    return switch (level) {
      case CRITICAL -> "Escopo em pressão crítica: proteção de capacidade acionada.";
      case HIGH -> "Escopo próximo do limite declarado.";
      case ELEVATED -> "Escopo com ocupação acima do confortável.";
      case NORMAL -> "Escopo dentro dos limites declarados.";
      case UNKNOWN ->
          backlogKnown
              ? "Pressão indeterminada nesta configuração."
              : "Fila pendente do escopo indisponível nesta configuração.";
    };
  }

  private Optional<WorkerBacklogView> backlog(CapacityPolicy policy) {
    if (policy.scopeType() != CapacityScopeType.WORKER_TYPE) {
      return Optional.empty();
    }
    WorkerBacklogQueryService service = backlogProvider.getIfAvailable();
    if (service == null) {
      return Optional.empty();
    }
    try {
      return Optional.of(service.backlog(WorkerType.valueOf(policy.scopeRef())));
    } catch (RuntimeException unavailable) {
      return Optional.empty();
    }
  }
}
