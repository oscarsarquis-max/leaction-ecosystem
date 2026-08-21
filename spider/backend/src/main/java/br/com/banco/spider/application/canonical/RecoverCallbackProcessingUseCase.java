package br.com.banco.spider.application.canonical;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.execution.callback.CallbackProcessingRecoveryService;
import br.com.banco.spider.execution.callback.CallbackProcessingRecoveryService.RecoverySummary;
import br.com.banco.spider.execution.support.SpiderClock;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class RecoverCallbackProcessingUseCase {

  private static final Logger log = LoggerFactory.getLogger(RecoverCallbackProcessingUseCase.class);

  private final CallbackOpsAuthorizationPort authorization;
  private final CallbackProcessingRecoveryService recovery;
  private final SpiderClock clock;

  public RecoverCallbackProcessingUseCase(
      CallbackOpsAuthorizationPort authorization,
      CallbackProcessingRecoveryService recovery,
      SpiderClock clock) {
    this.authorization = authorization;
    this.recovery = recovery;
    this.clock = clock;
  }

  public record Command(String actorRef, String reasonCode) {}

  public record Outcome(AuthorizationDecision decision, RecoverySummary summary) {}

  public Mono<Outcome> execute(Command command) {
    return authorization
        .authorize("callback.recover", command.actorRef())
        .flatMap(
            decision -> {
              if (decision != AuthorizationDecision.PERMIT) {
                log.info("event=recover_denied actorRef={} reasonCode=DENIED", command.actorRef());
                return Mono.just(new Outcome(decision, null));
              }
              log.info(
                  "event=recover_authorized actorRef={} reasonCode={}",
                  command.actorRef(),
                  command.reasonCode());
              return recovery
                  .recover(clock.now())
                  .map(summary -> new Outcome(AuthorizationDecision.PERMIT, summary));
            });
  }
}
