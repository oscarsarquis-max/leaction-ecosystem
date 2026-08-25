package br.com.banco.spider.operational.workers;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface DurableScheduleStorePort {

  DurableSchedule upsert(DurableSchedule schedule);

  Optional<DurableSchedule> findByCode(String scheduleCode);

  List<DurableSchedule> findAll();

  List<DurableSchedule> findEligible(Instant now, int limit);

  /**
   * Claim com compare-and-set. Só vence quando a versão observada é a atual, o agendamento está
   * habilitado e elegível, e a posse está livre (sem dono, lease vencido ou já é o mesmo worker).
   * Incrementa {@code fencingToken} e {@code version}.
   */
  Optional<DurableSchedule> tryClaim(
      String scheduleCode,
      long expectedVersion,
      String workerId,
      Instant now,
      Instant leaseUntil);

  /**
   * Conclui o ciclo. Só aceita quando o dono e o token de fencing conferem — um worker atrasado que
   * perdeu o lease nunca sobrescreve o agendamento do dono atual.
   */
  boolean complete(
      String scheduleCode,
      String workerId,
      long fencingToken,
      Instant now,
      ScheduleOutcome outcome,
      Instant nextEligibleAt);

  boolean isCurrentOwner(String scheduleCode, String workerId, long fencingToken);

  /** Semeia o catálogo quando o armazenamento está vazio; nunca sobrescreve linha existente. */
  void seed(List<DurableSchedule> schedules);

  /**
   * Antecipa o vencimento do lease sem remover a posse — usado apenas pelo laboratório de falhas
   * para demonstrar fencing. A posse continua sendo perdida por tempo, nunca por exclusão.
   */
  Optional<DurableSchedule> simulateLeaseExpiry(String scheduleCode, Instant expiredLeaseUntil);
}
