package br.com.banco.spider.execution.callback.delivery;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.callback.CallbackDeliveryCertainty;
import br.com.banco.spider.execution.callback.CallbackDeliveryDisposition;
import br.com.banco.spider.execution.callback.CallbackDeliveryEnvelope;
import br.com.banco.spider.execution.callback.CallbackDeliveryPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryResult;
import br.com.banco.spider.security.integrity.IntegrityProof;
import br.com.banco.spider.security.integrity.IntegrityVerificationResult;
import br.com.banco.spider.security.integrity.MessageIntegrityService;
import br.com.banco.spider.security.integrity.SigningInputCanonicalizerV1;
import br.com.banco.spider.security.integrity.SigningMaterial;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import reactor.core.publisher.Mono;

/**
 * Mock Callback Adapter — cenários controlados, sem rede. Pode validar IntegrityProof em testes.
 */
public class MockCallbackAdapter implements CallbackDeliveryPort {

  public enum Scenario {
    DELIVERED,
    RETRYABLE_FAILURE,
    NON_RETRYABLE_REJECTION,
    TIMEOUT,
    UNKNOWN
  }

  private final Scenario scenario;
  private final AtomicInteger invocations = new AtomicInteger();
  private final Map<String, Integer> byLogical = new ConcurrentHashMap<>();
  private final boolean requireProof;
  private Function<CallbackDeliveryEnvelope, Mono<Boolean>> proofChecker = e -> Mono.just(true);

  public MockCallbackAdapter(Scenario scenario) {
    this(scenario, false);
  }

  public MockCallbackAdapter(Scenario scenario, boolean requireProof) {
    this.scenario = scenario;
    this.requireProof = requireProof;
  }

  public void setProofChecker(Function<CallbackDeliveryEnvelope, Mono<Boolean>> proofChecker) {
    this.proofChecker = proofChecker;
  }

  /** Configura verificação via MessageIntegrityService (domínio CALLBACK_DELIVERY). */
  public void useIntegrityVerifier(MessageIntegrityService integrity) {
    this.proofChecker =
        envelope -> {
          IntegrityProof proof = envelope.integrityProof();
          if (proof == null) {
            return Mono.just(false);
          }
          SigningMaterial material =
              new SigningMaterial(
                  SigningInputCanonicalizerV1.DOMAIN_CALLBACK_DELIVERY,
                  proof.profileRef(),
                  proof.algorithm(),
                  proof.keyRef(),
                  proof.keyVersion(),
                  envelope.callbackContractVersion(),
                  "CALLBACK_DELIVERY",
                  envelope.executionId(),
                  envelope.logicalCallbackId(),
                  envelope.attemptNumber(),
                  proof.issuedAt(),
                  proof.expiresAt(),
                  proof.nonce(),
                  proof.payloadDigestAlgorithm(),
                  proof.payloadDigest(),
                  proof.canonicalizationVersion());
          return integrity.verify(material, proof).map(IntegrityVerificationResult::verified);
        };
  }

  public int invocationCount() {
    return invocations.get();
  }

  public int invocationsFor(String logicalCallbackId) {
    return byLogical.getOrDefault(logicalCallbackId, 0);
  }

  @Override
  public Mono<CallbackDeliveryResult> deliver(CallbackDeliveryEnvelope envelope) {
    Instant now = Instant.now();
    Mono<Boolean> check =
        requireProof || envelope.integrityProof() != null
            ? proofChecker.apply(envelope)
            : Mono.just(true);
    return check.flatMap(
        ok -> {
          if (!ok) {
            return Mono.just(
                CallbackDeliveryResult.failed(
                    CallbackDeliveryDisposition.REJECTED,
                    CallbackDeliveryCertainty.CONFIRMED,
                    now,
                    error("INVALID_INTEGRITY_PROOF", ErrorCategory.AUTHORIZATION)));
          }
          invocations.incrementAndGet();
          byLogical.merge(envelope.logicalCallbackId(), 1, Integer::sum);
          return switch (scenario) {
            case DELIVERED -> Mono.just(CallbackDeliveryResult.delivered(now));
            case RETRYABLE_FAILURE ->
                Mono.just(
                    CallbackDeliveryResult.failed(
                        CallbackDeliveryDisposition.FAILED,
                        CallbackDeliveryCertainty.CONFIRMED,
                        now,
                        error("CALLBACK_UNAVAILABLE", ErrorCategory.UNAVAILABLE)));
            case NON_RETRYABLE_REJECTION ->
                Mono.just(
                    CallbackDeliveryResult.failed(
                        CallbackDeliveryDisposition.REJECTED,
                        CallbackDeliveryCertainty.CONFIRMED,
                        now,
                        error("CALLBACK_REJECTED", ErrorCategory.AUTHORIZATION)));
            case TIMEOUT ->
                Mono.just(
                    CallbackDeliveryResult.failed(
                        CallbackDeliveryDisposition.TIMED_OUT,
                        CallbackDeliveryCertainty.UNCONFIRMED,
                        now,
                        error("CALLBACK_TIMEOUT", ErrorCategory.TIMEOUT)));
            case UNKNOWN ->
                Mono.just(
                    CallbackDeliveryResult.failed(
                        CallbackDeliveryDisposition.UNKNOWN,
                        CallbackDeliveryCertainty.UNKNOWN,
                        now,
                        error("CALLBACK_UNKNOWN", ErrorCategory.INTERNAL)));
          };
        });
  }

  private static CanonicalError error(String code, ErrorCategory category) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(category)
        .severity(ErrorSeverity.ERROR)
        .message(code)
        .retryable(category == ErrorCategory.UNAVAILABLE || category == ErrorCategory.TIMEOUT)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("mock_callback", null, null, null))
        .build();
  }
}
