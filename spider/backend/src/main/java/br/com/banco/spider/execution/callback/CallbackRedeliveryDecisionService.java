package br.com.banco.spider.execution.callback;

import java.time.Duration;
import java.time.Instant;
import org.springframework.stereotype.Service;

@Service
public class CallbackRedeliveryDecisionService {

  public CallbackRedeliveryDecision decide(
      CallbackDeliveryStatusDisposition disposition,
      ExecutionCallbackContext ctx,
      CallbackReconciliationPolicy policy,
      CallbackReconciliationRecord reconciliation,
      Instant now) {
    if (disposition != CallbackDeliveryStatusDisposition.CONFIRMED_NOT_FOUND) {
      return CallbackRedeliveryDecision.MANUAL_REVIEW_REQUIRED;
    }
    Instant graceEnd = reconciliation.startedAt().plus(policy.destinationVisibilityGracePeriod());
    if (now.isBefore(graceEnd)) {
      return CallbackRedeliveryDecision.WAIT_AND_QUERY_AGAIN;
    }
    if (!reconciliation.expiresAt().isAfter(now)) {
      return CallbackRedeliveryDecision.EXPIRE;
    }
    if (ctx.redeliverySafety() == CallbackRedeliverySafety.NEVER_AUTOMATIC) {
      return CallbackRedeliveryDecision.MANUAL_REVIEW_REQUIRED;
    }
    if (!policy.allowRedeliveryAfterConfirmedAbsence()) {
      return CallbackRedeliveryDecision.FINISH_CONFIRMED_ABSENT;
    }
    if (ctx.redeliverySafety() == CallbackRedeliverySafety.QUERY_BEFORE_REDELIVERY
        || ctx.redeliverySafety() == CallbackRedeliverySafety.IDEMPOTENT_BY_DELIVERY_KEY) {
      return CallbackRedeliveryDecision.REDISPATCH_ALLOWED;
    }
    return CallbackRedeliveryDecision.MANUAL_REVIEW_REQUIRED;
  }
}
