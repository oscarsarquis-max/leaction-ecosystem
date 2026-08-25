package br.com.banco.spider.operational.capacity;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * Buffer circular das decisões recentes de admissão.
 *
 * <p>Deliberadamente em memória: a decisão de admissão é um fato operacional efêmero e não pode
 * pagar o custo de uma escrita durável no caminho crítico. O contrato é explícito — depois de um
 * reinício o histórico recomeça vazio e a leitura declara essa limitação em {@code dataQuality}.
 */
public class CapacityDecisionStore {

  public static final int MAX_SIZE = 200;

  private final int maxSize;
  private final Deque<AdmissionDecision> decisions = new ArrayDeque<>();
  private long recorded;

  public CapacityDecisionStore(int maxSize) {
    this.maxSize = Math.max(1, Math.min(maxSize, MAX_SIZE));
  }

  public synchronized void record(AdmissionDecision decision) {
    if (decision == null) {
      return;
    }
    decisions.addFirst(decision);
    recorded++;
    while (decisions.size() > maxSize) {
      decisions.removeLast();
    }
  }

  /** Decisões mais recentes primeiro. */
  public synchronized List<AdmissionDecision> recent(int limit) {
    int effective = limit <= 0 ? maxSize : Math.min(limit, maxSize);
    List<AdmissionDecision> page = new ArrayList<>(effective);
    for (AdmissionDecision decision : decisions) {
      if (page.size() >= effective) {
        break;
      }
      page.add(decision);
    }
    return List.copyOf(page);
  }

  public synchronized long recordedTotal() {
    return recorded;
  }

  public synchronized boolean truncated() {
    return recorded > maxSize;
  }

  public int maxSize() {
    return maxSize;
  }
}
