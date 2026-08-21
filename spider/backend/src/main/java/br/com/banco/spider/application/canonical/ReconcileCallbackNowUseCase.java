package br.com.banco.spider.application.canonical;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.execution.callback.CallbackReconciliationProcessor;
import br.com.banco.spider.execution.callback.CallbackReconciliationProcessor.ReconciliationBatchResult;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/** Operação interna deny-by-default — sem Controller HTTP. */
@Service
public class ReconcileCallbackNowUseCase {

  private static final Logger log = LoggerFactory.getLogger(ReconcileCallbackNowUseCase.class);

  private final CallbackOpsAuthorizationPort authorization;
  private final CallbackReconciliationProcessor processor;
  private final SpiderClock clock;

  public ReconcileCallbackNowUseCase(
      CallbackOpsAuthorizationPort authorization,
      CallbackReconciliationProcessor processor,
      SpiderClock clock) {
    this.authorization = authorization;
    this.processor = processor;
    this.clock = clock;
  }

  public record Command(
      String actorRef, String reasonCode, String workerId, int batchSize) {}

  public record Outcome(AuthorizationDecision decision, ReconciliationBatchResult batch) {}

  public Mono<Outcome> execute(Command command) {
    return authorization
        .authorize("callback.reconcile", command.actorRef())
        .flatMap(
            decision -> {
              if (decision != AuthorizationDecision.PERMIT) {
                log.info(
                    "event=reconcile_denied actorRef={} reasonCode=DENIED", command.actorRef());
                return Mono.just(new Outcome(decision, null));
              }
              log.info(
                  "event=reconcile_authorized actorRef={} reasonCode={}",
                  command.actorRef(),
                  command.reasonCode());
              Instant now = clock.now();
              return processor
                  .processDue(
                      command.workerId() != null ? command.workerId() : "ops-worker",
                      now,
                      Math.min(Math.max(command.batchSize(), 1), 100))
                  .map(batch -> new Outcome(AuthorizationDecision.PERMIT, batch));
            });
  }
}
