package br.com.banco.spider.application.canonical;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.application.security.CanonicalExecutionAuthorizationPort;
import br.com.banco.spider.application.security.CanonicalIngressSecurityContext;
import br.com.banco.spider.application.security.ExecutionAuthorizationRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.contract.ExecutionIdentity;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.callback.CallbackContextFixationService;
import br.com.banco.spider.execution.engine.CanonicalExecutionEngine;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class SubmitCanonicalExecutionUseCase {

  private static final Logger log = LoggerFactory.getLogger(SubmitCanonicalExecutionUseCase.class);

  private final CanonicalExecutionAuthorizationPort authorization;
  private final CallbackContextFixationService callbackFixation;
  private final CanonicalExecutionEngine engine;
  private final SpiderClock clock;

  public SubmitCanonicalExecutionUseCase(
      CanonicalExecutionAuthorizationPort authorization,
      CallbackContextFixationService callbackFixation,
      CanonicalExecutionEngine engine,
      SpiderClock clock) {
    this.authorization = authorization;
    this.callbackFixation = callbackFixation;
    this.engine = engine;
    this.clock = clock;
  }

  public record SubmitCanonicalExecutionCommand(
      CanonicalExecutionRequest canonicalRequest,
      CanonicalIngressSecurityContext securityContext,
      br.com.banco.spider.application.security.AuthenticatedOriginator authenticatedOriginator,
      TraceDescriptor transportTrace,
      String transportIdempotencyKey,
      Instant receivedAt) {}

  public record SubmitOutcome(
      boolean success, CanonicalExecutionResult result, CanonicalError error, String httpHint) {}

  public Mono<SubmitOutcome> submit(SubmitCanonicalExecutionCommand command) {
    CanonicalExecutionRequest request = command.canonicalRequest();
    CanonicalIngressSecurityContext sec = command.securityContext();
    var originator = command.authenticatedOriginator();

    if (!Objects.equals(sec.originatorId(), request.origin().originatorId())) {
      log.info("event=authz_decision reasonCode=ORIGINATOR_MISMATCH");
      return Mono.just(fail(error("ORIGINATOR_MISMATCH", "Authenticated originator mismatch", ErrorCategory.AUTHORIZATION), "403"));
    }
    if (!Objects.equals(sec.channel(), request.origin().channel())) {
      log.info("event=authz_decision reasonCode=CHANNEL_MISMATCH");
      return Mono.just(fail(error("CHANNEL_MISMATCH", "Authenticated channel mismatch", ErrorCategory.AUTHORIZATION), "403"));
    }

    return authorization
        .authorize(
            new ExecutionAuthorizationRequest(
                originator,
                request.target().capability(),
                request.target().operation(),
                sec.channel(),
                request.contract().contractVersion(),
                null))
        .flatMap(
            decision -> {
              if (decision != AuthorizationDecision.PERMIT) {
                log.info("event=authz_decision reasonCode={}", decision);
                return Mono.just(
                    fail(
                        error("EXECUTION_DENIED", "Capability/operation not authorized", ErrorCategory.AUTHORIZATION),
                        decision == AuthorizationDecision.INDETERMINATE ? "500" : "403"));
              }

              CanonicalExecutionRequest reconciled =
                  reconcile(request, command.transportTrace(), command.transportIdempotencyKey());
              if (reconciled == null) {
                return Mono.just(
                    fail(
                        error("CONTRACT_HEADER_MISMATCH", "Idempotency or trace header/body mismatch", ErrorCategory.CONTRACT),
                        "400"));
              }

              return callbackFixation
                  .fixIfPresent(reconciled)
                  .flatMap(
                      fixation -> {
                        if (!fixation.ok()) {
                          log.info(
                              "event=submission_rejected reasonCode={}",
                              fixation.error().code());
                          return Mono.just(fail(fixation.error(), "422"));
                        }
                        log.info(
                            "event=submission_accepted executionId={} reasonCode=OK",
                            reconciled.execution().executionId());
                        return engine
                            .execute(reconciled, sec.principalRef())
                            .map(r -> new SubmitOutcome(true, r, null, null));
                      });
            });
  }

  private CanonicalExecutionRequest reconcile(
      CanonicalExecutionRequest request, TraceDescriptor transportTrace, String transportKey) {
    String bodyKey = request.execution().idempotencyKey();
    if (transportKey != null && !transportKey.isBlank()) {
      if (transportKey.length() > 128 || !transportKey.matches("[A-Za-z0-9._:-]+")) {
        return null;
      }
      if (bodyKey != null && !bodyKey.isBlank() && !bodyKey.equals(transportKey)) {
        return null;
      }
      if (bodyKey == null || bodyKey.isBlank()) {
        request =
            CanonicalExecutionRequest.builder()
                .contract(request.contract())
                .execution(
                    new ExecutionIdentity(
                        request.execution().executionId(),
                        request.execution().timestamp(),
                        transportKey))
                .contextRef(request.contextRef())
                .origin(request.origin())
                .trace(request.trace())
                .target(request.target())
                .payload(request.payload())
                .executionPolicy(request.executionPolicy())
                .callbackRef(request.callbackRef())
                .build();
      }
    }

    if (transportTrace != null) {
      if (!transportTrace.correlationId().equals(request.trace().correlationId())) {
        // correlation may differ; require traceparent coherence when both present
      }
      if (request.trace().traceparent() != null
          && transportTrace.traceparent() != null
          && !request.trace().traceparent().equals(transportTrace.traceparent())) {
        return null;
      }
    }
    return request;
  }

  private static SubmitOutcome fail(CanonicalError error, String httpHint) {
    return new SubmitOutcome(false, null, error, httpHint);
  }

  private static CanonicalError error(String code, String message, ErrorCategory category) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(category)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("submit_canonical", null, null, null))
        .build();
  }
}
