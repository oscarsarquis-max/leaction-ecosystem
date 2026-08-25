package br.com.banco.spider.operational.workers;

import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Demonstrações controladas do runtime de workers para o laboratório de falhas.
 *
 * <p>O harness nunca mexe nos agendamentos reais do catálogo nem derruba a JVM: ele opera em um
 * agendamento dedicado ({@value #HARNESS_SCHEDULE_CODE}) que o coordenador jamais reivindica,
 * porque só reconhece códigos do catálogo fechado.
 */
public class FailureLabWorkerHarness {

  public static final String HARNESS_SCHEDULE_CODE = "sched:failure-lab-harness@1";
  private static final String WORKER_A = "lab:worker-a";
  private static final String WORKER_B = "lab:worker-b";
  private static final Duration LEASE = Duration.ofSeconds(30);
  private static final Duration INTERVAL = Duration.ofSeconds(5);

  private final DurableScheduleStorePort scheduleStore;
  private final WorkerInstanceStorePort instanceStore;
  private final WorkerBacklogQueryService backlogService;
  private final RequestWorkerDrainUseCase drainUseCase;
  private final SpiderClock clock;

  public FailureLabWorkerHarness(
      DurableScheduleStorePort scheduleStore,
      WorkerInstanceStorePort instanceStore,
      WorkerBacklogQueryService backlogService,
      RequestWorkerDrainUseCase drainUseCase,
      SpiderClock clock) {
    this.scheduleStore = scheduleStore;
    this.instanceStore = instanceStore;
    this.backlogService = backlogService;
    this.drainUseCase = drainUseCase;
    this.clock = clock;
  }

  /** Claim sem conclusão, lease vencido, novo claim e recusa da conclusão atrasada. */
  public Map<String, String> crashAfterClaim() {
    Map<String, String> facts = new LinkedHashMap<>();
    DurableSchedule schedule = resetHarnessSchedule();
    Instant now = clock.now();
    Optional<DurableSchedule> first =
        scheduleStore.tryClaim(
            HARNESS_SCHEDULE_CODE, schedule.version(), WORKER_A, now, now.plus(LEASE));
    if (first.isEmpty()) {
      facts.put("workerClaim", "NOT_ACQUIRED");
      return Map.copyOf(facts);
    }
    facts.put("workerClaim", "ACQUIRED");
    long staleFencing = first.get().fencingToken();

    scheduleStore.simulateLeaseExpiry(HARNESS_SCHEDULE_CODE, now.minusSeconds(1));
    DurableSchedule expired =
        scheduleStore.findByCode(HARNESS_SCHEDULE_CODE).orElseThrow();
    facts.put("workerLease", expired.leaseExpiredAt(now) ? "EXPIRED" : "HELD");

    Optional<DurableSchedule> second =
        scheduleStore.tryClaim(
            HARNESS_SCHEDULE_CODE, expired.version(), WORKER_B, now, now.plus(LEASE));
    facts.put(
        "workerReclaim",
        second.isPresent() && second.get().fencingToken() > staleFencing
            ? "ACQUIRED_AFTER_LEASE_EXPIRY"
            : "NOT_ACQUIRED");

    boolean staleCompleted =
        scheduleStore.complete(
            HARNESS_SCHEDULE_CODE,
            WORKER_A,
            staleFencing,
            now,
            ScheduleOutcome.SUCCESS,
            now.plus(INTERVAL));
    facts.put("workerFencing", staleCompleted ? "STALE_COMPLETION_ACCEPTED" : "STALE_COMPLETION_REJECTED");
    return Map.copyOf(facts);
  }

  /** Dois workers disputam o mesmo agendamento a partir da mesma versão observada. */
  public Map<String, String> dualContention() {
    Map<String, String> facts = new LinkedHashMap<>();
    DurableSchedule schedule = resetHarnessSchedule();
    Instant now = clock.now();
    long observedVersion = schedule.version();
    Optional<DurableSchedule> a =
        scheduleStore.tryClaim(
            HARNESS_SCHEDULE_CODE, observedVersion, WORKER_A, now, now.plus(LEASE));
    Optional<DurableSchedule> b =
        scheduleStore.tryClaim(
            HARNESS_SCHEDULE_CODE, observedVersion, WORKER_B, now, now.plus(LEASE));
    int winners = (a.isPresent() ? 1 : 0) + (b.isPresent() ? 1 : 0);
    facts.put("workerContention", winners == 1 ? "SINGLE_WINNER" : "WINNERS_" + winners);
    a.or(() -> b)
        .ifPresent(
            claimed ->
                scheduleStore.complete(
                    HARNESS_SCHEDULE_CODE,
                    claimed.ownerWorkerId(),
                    claimed.fencingToken(),
                    now,
                    ScheduleOutcome.SUCCESS,
                    now.plus(INTERVAL)));
    return Map.copyOf(facts);
  }

  /** Drenagem: o worker marcado para drenar deixa de aceitar novos claims. */
  public Map<String, String> gracefulDrain() {
    Map<String, String> facts = new LinkedHashMap<>();
    Instant now = clock.now();
    WorkerInstance labWorker =
        instanceStore.upsert(
            WorkerInstance.starting(
                WORKER_A, "lab-runtime", WorkerType.PROTECTED_ENVELOPE_MAINTENANCE, now));
    Optional<WorkerInstance> draining = drainUseCase.requestDrain(labWorker.workerId(), "failure-lab");
    facts.put(
        "workerDrain",
        draining.filter(WorkerInstance::draining).isPresent() ? "DRAINING" : "NOT_DRAINING");
    facts.put(
        "workerDrainClaims",
        draining.map(worker -> worker.draining() ? "NO_NEW_CLAIMS" : "STILL_CLAIMING").orElse("UNKNOWN"));
    draining.ifPresent(
        worker -> instanceStore.upsert(worker.withStatus(WorkerInstanceStatus.STOPPED, now)));
    return Map.copyOf(facts);
  }

  /** Backlog observado nas fontes canônicas — sem inserir trabalho artificial. */
  public Map<String, String> backlogAccumulation() {
    Map<String, String> facts = new LinkedHashMap<>();
    WorkerBacklogStatus worst =
        backlogService.backlogs().stream()
            .map(WorkerBacklogView::status)
            .max(java.util.Comparator.comparingInt(FailureLabWorkerHarness::severity))
            .orElse(WorkerBacklogStatus.UNKNOWN);
    facts.put("workerBacklog", worst.name());
    facts.put(
        "workerBacklogSeeded",
        "NOT_SEEDED_READ_ONLY_OBSERVATION");
    return Map.copyOf(facts);
  }

  /** Reinício: o agendamento concluído mantém sua próxima elegibilidade após nova leitura. */
  public Map<String, String> restartRecovery() {
    Map<String, String> facts = new LinkedHashMap<>();
    DurableSchedule schedule = resetHarnessSchedule();
    Instant now = clock.now();
    Optional<DurableSchedule> claimed =
        scheduleStore.tryClaim(
            HARNESS_SCHEDULE_CODE, schedule.version(), WORKER_A, now, now.plus(LEASE));
    if (claimed.isEmpty()) {
      facts.put("workerRestart", "NOT_ACQUIRED");
      return Map.copyOf(facts);
    }
    Instant expectedNext = now.plus(INTERVAL);
    scheduleStore.complete(
        HARNESS_SCHEDULE_CODE,
        WORKER_A,
        claimed.get().fencingToken(),
        now,
        ScheduleOutcome.SUCCESS,
        expectedNext);
    Optional<DurableSchedule> reloaded = scheduleStore.findByCode(HARNESS_SCHEDULE_CODE);
    boolean survived =
        reloaded
            .map(
                current ->
                    current.ownerWorkerId() == null
                        && expectedNext.equals(current.nextEligibleAt())
                        && current.lastOutcome() == ScheduleOutcome.SUCCESS)
            .orElse(false);
    facts.put("workerRestart", survived ? "SCHEDULE_STATE_SURVIVED" : "SCHEDULE_STATE_LOST");
    return Map.copyOf(facts);
  }

  private DurableSchedule resetHarnessSchedule() {
    Instant now = clock.now();
    DurableSchedule current =
        scheduleStore.findByCode(HARNESS_SCHEDULE_CODE).orElse(null);
    long version = current == null ? 0L : current.version() + 1;
    return scheduleStore.upsert(
        new DurableSchedule(
            HARNESS_SCHEDULE_CODE,
            version,
            WorkerRuntimeCatalog.SCHEDULE_DEFINITION_VERSION,
            WorkerType.PROTECTED_ENVELOPE_MAINTENANCE,
            true,
            INTERVAL,
            now.minusSeconds(1),
            null,
            null,
            null,
            null,
            null,
            current == null ? 0L : current.fencingToken()));
  }

  private static int severity(WorkerBacklogStatus status) {
    return switch (status) {
      case EMPTY -> 0;
      case NORMAL -> 1;
      case UNKNOWN -> 2;
      case ACCUMULATING -> 3;
      case STALE -> 4;
    };
  }
}
