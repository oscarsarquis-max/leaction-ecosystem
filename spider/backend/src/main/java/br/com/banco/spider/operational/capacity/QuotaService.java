package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Quotas por janela fixa, uma contagem por escopo. A janela avança de forma preguiçosa na primeira
 * consulta após o vencimento — não há tarefa periódica de limpeza, então a leitura e o consumo veem
 * sempre a mesma fronteira de janela.
 */
public class QuotaService {

  private final SpiderClock clock;
  private final Map<String, Window> windows = new ConcurrentHashMap<>();

  public QuotaService(SpiderClock clock) {
    this.clock = clock;
  }

  /** Consome uma unidade; falso quando a janela corrente já está esgotada. */
  public boolean tryConsume(String scopeKey, int quotaPerWindow, Duration window) {
    if (scopeKey == null || quotaPerWindow <= 0 || window == null) {
      return true;
    }
    Window current = windows.computeIfAbsent(scopeKey, key -> new Window());
    return current.consume(quotaPerWindow, window, clock.now());
  }

  /** Uso da janela corrente sem consumir. */
  public int used(String scopeKey, Duration window) {
    Window current = scopeKey == null ? null : windows.get(scopeKey);
    if (current == null) {
      return 0;
    }
    return current.used(window == null ? Duration.ofMinutes(1) : window, clock.now());
  }

  public Instant windowStartedAt(String scopeKey) {
    Window current = scopeKey == null ? null : windows.get(scopeKey);
    return current == null ? null : current.startedAt();
  }

  private static final class Window {
    private Instant startedAt;
    private int count;

    synchronized boolean consume(int quotaPerWindow, Duration window, Instant now) {
      roll(window, now);
      if (count >= quotaPerWindow) {
        return false;
      }
      count++;
      return true;
    }

    synchronized int used(Duration window, Instant now) {
      roll(window, now);
      return count;
    }

    synchronized Instant startedAt() {
      return startedAt;
    }

    private void roll(Duration window, Instant now) {
      if (startedAt == null || !now.isBefore(startedAt.plus(window))) {
        startedAt = now;
        count = 0;
      }
    }
  }
}
