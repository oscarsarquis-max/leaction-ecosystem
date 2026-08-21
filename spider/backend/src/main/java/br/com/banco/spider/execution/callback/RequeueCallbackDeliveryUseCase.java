package br.com.banco.spider.execution.callback;

import br.com.banco.spider.application.security.AuthorizationDecision;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/** Reprocessamento interno deny-by-default — sem endpoint público. */
@Service
public class RequeueCallbackDeliveryUseCase {

  private static final Logger log = LoggerFactory.getLogger(RequeueCallbackDeliveryUseCase.class);

  public record RequeueCommand(
      String outboxId, String principalRef, Instant requestedAt) {}

  public record RequeueOutcome(AuthorizationDecision decision, String reasonCode) {}

  public Mono<RequeueOutcome> requeue(RequeueCommand command) {
    log.info(
        "event=requeue_denied outboxId={} reasonCode=DENY_DEFAULT",
        command.outboxId());
    return Mono.just(new RequeueOutcome(AuthorizationDecision.DENY, "REQUEUE_DENIED_DEFAULT"));
  }
}
