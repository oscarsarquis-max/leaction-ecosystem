package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.workers.DurableSchedule;
import br.com.banco.spider.operational.workers.DurableScheduleStorePort;
import br.com.banco.spider.operational.workers.WorkerRuntimeCatalog;
import br.com.banco.spider.operational.workers.WorkerType;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import org.springframework.beans.factory.ObjectProvider;

/**
 * Demonstrações controladas do governo de capacidade para o laboratório de falhas.
 *
 * <p>O harness nunca usa as políticas publicadas: cada proteção é exercida contra uma política de
 * laboratório em escopo dedicado, de modo que saturar um bulkhead ou abrir um disjuntor aqui não
 * altera a admissão de nenhum trabalho real. As reservas feitas durante a demonstração são sempre
 * liberadas antes do retorno.
 */
public class FailureLabCapacityHarness {

  public static final String LAB_SCHEDULE_CODE = "sched:failure-lab-capacity@1";

  private static final String LAB_VERSION = "1.0";
  private static final Duration LAB_WINDOW = Duration.ofMinutes(1);
  private static final Duration LONG_OPEN = Duration.ofMinutes(5);

  private final CapacityAdmissionService admission;
  private final BulkheadService bulkheads;
  private final CircuitBreakerService circuits;
  private final QuotaService quotas;
  private final SpiderClock clock;
  private final ObjectProvider<DurableScheduleStorePort> scheduleStoreProvider;

  public FailureLabCapacityHarness(
      CapacityAdmissionService admission,
      BulkheadService bulkheads,
      CircuitBreakerService circuits,
      QuotaService quotas,
      SpiderClock clock,
      ObjectProvider<DurableScheduleStorePort> scheduleStoreProvider) {
    this.admission = admission;
    this.bulkheads = bulkheads;
    this.circuits = circuits;
    this.quotas = quotas;
    this.clock = clock;
    this.scheduleStoreProvider = scheduleStoreProvider;
  }

  /** Bulkhead cheio: o pedido seguinte é recusado por capacidade e a vaga é devolvida no fim. */
  public Map<String, String> bulkheadSaturation() {
    Map<String, String> facts = baseFacts();
    CapacityPolicy policy = concurrencyPolicy("bulkhead", 1);
    String scopeKey = policy.scopeKey();
    bulkheads.register(scopeKey, 1);
    boolean reserved = bulkheads.tryAcquire(scopeKey, 1);
    facts.put("capacityBulkheadReserved", reserved ? "ACQUIRED" : "NOT_ACQUIRED");
    try {
      AdmissionDecision decision = admission.evaluate(request(policy), policy);
      facts.put("capacityBulkhead", decision.result().name());
      facts.put("capacityBulkheadMonitorOnly", String.valueOf(decision.monitorOnly()));
    } finally {
      if (reserved) {
        bulkheads.release(scopeKey);
      }
    }
    facts.put(
        "capacityBulkheadReleased",
        bulkheads.occupied(scopeKey) == 0 ? "RELEASED_WITHOUT_LEAK" : "OCCUPANCY_LEAKED");
    return Map.copyOf(facts);
  }

  /** Disjuntor aberto recusa admissão; em outro escopo a prova bem-sucedida o fecha de novo. */
  public Map<String, String> circuitOpenAndRecover() {
    Map<String, String> facts = baseFacts();
    CapacityPolicy opening = circuitPolicy("circuit-open", LONG_OPEN);
    for (int attempt = 0; attempt < opening.circuitFailureThreshold(); attempt++) {
      circuits.recordFailure(opening.scopeKey(), opening);
    }
    facts.put("capacityCircuitPhase", circuits.phase(opening.scopeKey()).name());
    facts.put(
        "capacityCircuitAdmission",
        admission.evaluate(request(opening), opening).result().name());

    // Prova de recuperação em escopo próprio: com duração de abertura nula a fase avança para
    // HALF_OPEN na primeira verificação, sem depender de tempo de parede.
    CapacityPolicy recovering = circuitPolicy("circuit-recover", Duration.ZERO);
    for (int attempt = 0; attempt < recovering.circuitFailureThreshold(); attempt++) {
      circuits.recordFailure(recovering.scopeKey(), recovering);
    }
    boolean probeAllowed = circuits.allowRequest(recovering.scopeKey(), recovering);
    facts.put("capacityCircuitProbe", probeAllowed ? "PROBE_ALLOWED" : "PROBE_BLOCKED");
    if (probeAllowed) {
      circuits.recordSuccess(recovering.scopeKey(), recovering);
    }
    facts.put("capacityCircuitRecovery", circuits.phase(recovering.scopeKey()).name());
    return Map.copyOf(facts);
  }

  /** Quota da janela esgotada: a admissão passa a recusar até a janela virar. */
  public Map<String, String> quotaExhaustion() {
    Map<String, String> facts = baseFacts();
    CapacityPolicy policy = quotaPolicy();
    String observed = null;
    for (int attempt = 0; attempt <= policy.limits().quotaPerWindow(); attempt++) {
      AdmissionDecision decision = admission.evaluate(request(policy), policy);
      observed = decision.result().name();
      if (decision.result() == AdmissionResult.REJECTED_QUOTA) {
        break;
      }
    }
    facts.put("capacityQuota", observed == null ? "NOT_EVALUATED" : observed);
    facts.put(
        "capacityQuotaUsed",
        String.valueOf(quotas.used(policy.scopeKey(), policy.limits().window())));
    return Map.copyOf(facts);
  }

  /** Fila pendente no limite duro: a carga é descartada em vez de entrar no runtime. */
  public Map<String, String> backlogHardLimit() {
    Map<String, String> facts = baseFacts();
    CapacityPolicy policy = backlogPolicy();
    AdmissionDecision decision = admission.evaluate(backlogRequest(policy), policy);
    boolean shed = decision.result() == AdmissionResult.SHED;
    facts.put("capacityBacklog", shed ? decision.result().name() : "BACKLOG_NOT_OBSERVED");
    facts.put(
        "capacityShedReason",
        decision.shedReason() == null ? "NONE" : decision.shedReason().name());
    return Map.copyOf(facts);
  }

  /**
   * Recusa antes do claim: o token de fencing do agendamento durável fica intacto. É a propriedade
   * que impede uma rajada de recusas de queimar posse sem nenhum trabalho executado.
   */
  public Map<String, String> loadSheddingKeepsFencing() {
    Map<String, String> facts = baseFacts();
    DurableScheduleStorePort store = scheduleStoreProvider.getIfAvailable();
    if (store == null) {
      facts.put("capacityFencing", "SCHEDULE_STORE_UNAVAILABLE");
      return Map.copyOf(facts);
    }
    DurableSchedule before = resetLabSchedule(store);
    CapacityPolicy policy = concurrencyPolicy("fencing", 1);
    String scopeKey = policy.scopeKey();
    bulkheads.register(scopeKey, 1);
    boolean reserved = bulkheads.tryAcquire(scopeKey, 1);
    AdmissionDecision decision;
    try {
      decision = admission.evaluate(request(policy), policy);
    } finally {
      if (reserved) {
        bulkheads.release(scopeKey);
      }
    }
    facts.put("capacityShedAdmission", decision.result().name());
    DurableSchedule after = store.findByCode(LAB_SCHEDULE_CODE).orElse(before);
    boolean unchanged =
        after.fencingToken() == before.fencingToken() && after.ownerWorkerId() == null;
    facts.put("capacityFencing", unchanged ? "UNCHANGED" : "CHANGED");
    // Chave sem a palavra reservada de credencial: a redação do laboratório descarta o fato inteiro
    // quando o nome parece sensível, e a marca de posse é apenas um contador.
    facts.put("capacityFencingMark", String.valueOf(after.fencingToken()));
    return Map.copyOf(facts);
  }

  private Map<String, String> baseFacts() {
    Map<String, String> facts = new LinkedHashMap<>();
    facts.put("capacityMode", admission.mode().name());
    return facts;
  }

  private AdmissionRequest request(CapacityPolicy policy) {
    return new AdmissionRequest(
        "failure-lab:" + policy.code(),
        CapacityScopeType.SCHEDULE,
        policy.scopeRef(),
        null,
        policy.scopeRef(),
        null,
        null,
        clock.now(),
        "failure-lab-capacity");
  }

  private AdmissionRequest backlogRequest(CapacityPolicy policy) {
    return new AdmissionRequest(
        "failure-lab:" + policy.code(),
        CapacityScopeType.SCHEDULE,
        policy.scopeRef(),
        WorkerType.CALLBACK_DELIVERY.name(),
        policy.scopeRef(),
        null,
        null,
        clock.now(),
        "failure-lab-capacity");
  }

  private static CapacityPolicy concurrencyPolicy(String suffix, int maxConcurrency) {
    return labPolicy(
        suffix,
        new CapacityLimit(
            maxConcurrency,
            CapacityLimit.NO_LIMIT,
            CapacityLimit.NO_LIMIT,
            0,
            LAB_WINDOW,
            Duration.ZERO),
        0,
        Duration.ZERO);
  }

  private static CapacityPolicy circuitPolicy(String suffix, Duration openDuration) {
    return labPolicy(
        suffix,
        new CapacityLimit(
            0, CapacityLimit.NO_LIMIT, CapacityLimit.NO_LIMIT, 0, LAB_WINDOW, Duration.ZERO),
        2,
        openDuration);
  }

  private static CapacityPolicy quotaPolicy() {
    return labPolicy(
        "quota",
        new CapacityLimit(
            0, CapacityLimit.NO_LIMIT, CapacityLimit.NO_LIMIT, 1, LAB_WINDOW, Duration.ZERO),
        0,
        Duration.ZERO);
  }

  private static CapacityPolicy backlogPolicy() {
    return labPolicy(
        "backlog",
        new CapacityLimit(0, 0, 0, 0, LAB_WINDOW, Duration.ZERO),
        0,
        Duration.ZERO);
  }

  private static CapacityPolicy labPolicy(
      String suffix, CapacityLimit limits, int circuitFailureThreshold, Duration openDuration) {
    return new CapacityPolicy(
        "capacity:failure-lab:" + suffix,
        LAB_VERSION,
        CapacityScopeType.SCHEDULE,
        "sched:failure-lab-capacity-" + suffix + "@1",
        CapacityPolicyState.ACTIVE,
        limits,
        circuitFailureThreshold,
        LAB_WINDOW,
        openDuration,
        1,
        1,
        true);
  }

  /** Agendamento dedicado do laboratório: o coordenador jamais o reivindica. */
  private DurableSchedule resetLabSchedule(DurableScheduleStorePort store) {
    Instant now = clock.now();
    Optional<DurableSchedule> current = store.findByCode(LAB_SCHEDULE_CODE);
    long version = current.map(schedule -> schedule.version() + 1).orElse(0L);
    return store.upsert(
        new DurableSchedule(
            LAB_SCHEDULE_CODE,
            version,
            WorkerRuntimeCatalog.SCHEDULE_DEFINITION_VERSION,
            WorkerType.PROTECTED_ENVELOPE_MAINTENANCE,
            true,
            Duration.ofSeconds(5),
            now.minusSeconds(1),
            null,
            null,
            null,
            null,
            null,
            current.map(DurableSchedule::fencingToken).orElse(0L)));
  }
}
