package br.com.banco.spider.infrastructure.persistence;

import java.util.concurrent.Callable;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Scheduler;
import reactor.core.scheduler.Schedulers;

/** Centraliza isolamento de operações bloqueantes (JPA) fora da event loop. */
@Component
public class BlockingPersistenceSupport {

  private final Scheduler scheduler;

  @org.springframework.beans.factory.annotation.Autowired
  public BlockingPersistenceSupport() {
    this.scheduler = Schedulers.boundedElastic();
  }

  public BlockingPersistenceSupport(Scheduler scheduler) {
    this.scheduler = scheduler;
  }

  public <T> Mono<T> defer(Callable<T> callable) {
    return Mono.fromCallable(callable).subscribeOn(scheduler);
  }

  public Scheduler scheduler() {
    return scheduler;
  }
}
