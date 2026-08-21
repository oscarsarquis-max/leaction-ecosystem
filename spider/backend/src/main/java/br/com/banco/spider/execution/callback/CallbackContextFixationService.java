package br.com.banco.spider.execution.callback;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.canonical.versioning.VersionedReference;
import br.com.banco.spider.execution.fingerprint.IdempotencyKeyHashPort;
import br.com.banco.spider.execution.persistence.port.ExecutionCallbackContextStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/** Valida e fixa callback context antes do primeiro efeito externo. */
@Service
public class CallbackContextFixationService {

  private static final Logger log = LoggerFactory.getLogger(CallbackContextFixationService.class);

  private final CallbackDefinitionCatalogPort definitionCatalog;
  private final CallbackDeliveryPolicyCatalogPort policyCatalog;
  private final CallbackAuthorizationPort authorization;
  private final ExecutionCallbackContextStorePort contextStore;
  private final IdempotencyKeyHashPort keyHash;
  private final SpiderClock clock;

  public CallbackContextFixationService(
      CallbackDefinitionCatalogPort definitionCatalog,
      CallbackDeliveryPolicyCatalogPort policyCatalog,
      CallbackAuthorizationPort authorization,
      ExecutionCallbackContextStorePort contextStore,
      IdempotencyKeyHashPort keyHash,
      SpiderClock clock) {
    this.definitionCatalog = definitionCatalog;
    this.policyCatalog = policyCatalog;
    this.authorization = authorization;
    this.contextStore = contextStore;
    this.keyHash = keyHash;
    this.clock = clock;
  }

  public record FixationResult(boolean ok, ExecutionCallbackContext context, CanonicalError error) {}

  public Mono<FixationResult> fixIfPresent(CanonicalExecutionRequest request) {
    VersionedReference ref = request.callbackRef();
    if (ref == null) {
      return Mono.just(new FixationResult(true, null, null));
    }
    String exact = ref.ref() + (ref.version() != null ? "@" + ref.version() : "");
    // aceitar "callback:code@1.0" já no ref
    String lookup = ref.version() != null ? ref.ref() + "@" + ref.version() : ref.ref();
    Optional<CallbackDefinition> defOpt = definitionCatalog.findByExactRef(lookup);
    if (defOpt.isEmpty() && ref.ref().contains("@")) {
      defOpt = definitionCatalog.findByExactRef(ref.ref());
    }
    if (defOpt.isEmpty() || !defOpt.get().isEligible()) {
      return Mono.just(
          new FixationResult(
              false, null, error("CALLBACK_UNKNOWN", "Callback definition not published", ErrorCategory.RESOLUTION)));
    }
    CallbackDefinition def = defOpt.get();
    Optional<CallbackDeliveryPolicy> policy =
        policyCatalog.findByExactRef(def.deliveryPolicyRef()).filter(CallbackDeliveryPolicy::isEligible);
    if (policy.isEmpty()) {
      return Mono.just(
          new FixationResult(
              false, null, error("CALLBACK_POLICY_MISSING", "Delivery policy missing", ErrorCategory.RESOLUTION)));
    }
    try {
      CallbackProjectionKind.valueOf(def.projectionRef());
    } catch (Exception ex) {
      return Mono.just(
          new FixationResult(
              false, null, error("CALLBACK_PROJECTION_UNKNOWN", "Unknown projection", ErrorCategory.CONTRACT)));
    }

    return authorization
        .authorize(
            new CallbackAuthorizationRequest(
                def,
                null,
                request.origin().originatorId(),
                null,
                null,
                List.of(def.maximumDataClassification()),
                def.projectionRef()))
        .map(
            decision -> {
              if (decision != AuthorizationDecision.PERMIT) {
                return new FixationResult(
                    false,
                    null,
                    error("CALLBACK_DENIED", "Callback not authorized", ErrorCategory.AUTHORIZATION));
              }
              Instant now = clock.now();
              String deliveryKey =
                  "cb:" + request.execution().executionId() + ":" + def.exactRef();
              ExecutionCallbackContext ctx =
                  new ExecutionCallbackContext(
                      request.execution().executionId(),
                      def.exactRef(),
                      def.bindingRef(),
                      def.callbackContractRef(),
                      def.securityProfileRef(),
                      def.deliveryPolicyRef(),
                      def.projectionRef(),
                      request.origin().originatorId(),
                      def.integrityRef(),
                      now,
                      def.confirmationMode(),
                      def.statusQueryBindingRef(),
                      def.reconciliationPolicyRef(),
                      def.redeliverySafety(),
                      keyHash.hash(deliveryKey));
              contextStore.insert(ctx);
              log.info(
                  "event=callback_context_fixed executionId={} callbackRef={}",
                  ctx.executionId(),
                  ctx.callbackDefinitionRef());
              return new FixationResult(true, ctx, null);
            });
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
        .source(new CanonicalError.ErrorSource("callback_fixation", null, null, null))
        .build();
  }
}
