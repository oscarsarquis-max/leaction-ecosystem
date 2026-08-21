package br.com.banco.spider.integration.inbound.http.canonical;

import static org.assertj.core.api.Assertions.assertThat;

import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.signal.ExternalSignalApplicationPort;
import br.com.banco.spider.execution.signal.ExternalSignalEnvelope;
import br.com.banco.spider.execution.signal.ExternalSignalIngressOutcome;
import br.com.banco.spider.execution.signal.ExternalSignalIngressResult;
import br.com.banco.spider.execution.signal.ExternalSignalProcessingResult;
import br.com.banco.spider.execution.signal.ExternalSignalProcessingStatus;
import br.com.banco.spider.execution.signal.SignalCompletion;
import br.com.banco.spider.execution.signal.SignalSecurityContext;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

/** HTTP durable routing: durable path não chama inline resume. */
class DurableHttpRoutingStrategyTest {

  @Test
  void durableHandlerDoesNotCallInlineApplicationPort() {
    AtomicBoolean inlineCalled = new AtomicBoolean(false);
    AtomicBoolean ingressCalled = new AtomicBoolean(false);

    ExternalSignalApplicationPort inline =
        envelope -> {
          inlineCalled.set(true);
          return Mono.just(
              ExternalSignalProcessingResult.of(
                  ExternalSignalProcessingStatus.ACCEPTED_AND_RESUMED,
                  envelope.executionId(),
                  null,
                  null,
                  null,
                  null));
        };

    ExternalSignalHttpApplicationPort durable =
        envelope -> {
          ingressCalled.set(true);
          return Mono.just(
                  ExternalSignalIngressResult.of(
                      ExternalSignalIngressOutcome.ACCEPTED_PENDING_APPLICATION, "APPLY_PENDING"))
              .map(
                  r ->
                      ExternalSignalProcessingResult.of(
                          ExternalSignalProcessingStatus.ACCEPTED_AND_TERMINATED,
                          null,
                          null,
                          null,
                          null,
                          null));
        };

    ExternalSignalHttpApplicationPort chosenDurable = durable;
    ExternalSignalHttpApplicationPort chosenInline = inline::process;

    ExternalSignalEnvelope env = sampleEnvelope();

    StepVerifier.create(chosenDurable.handle(env))
        .assertNext(
            r ->
                assertThat(r.processingStatus())
                    .isEqualTo(ExternalSignalProcessingStatus.ACCEPTED_AND_TERMINATED))
        .verifyComplete();
    assertThat(ingressCalled.get()).isTrue();
    assertThat(inlineCalled.get()).isFalse();

    StepVerifier.create(chosenInline.handle(env))
        .assertNext(
            r ->
                assertThat(r.processingStatus())
                    .isEqualTo(ExternalSignalProcessingStatus.ACCEPTED_AND_RESUMED))
        .verifyComplete();
    assertThat(inlineCalled.get()).isTrue();
  }

  private static ExternalSignalEnvelope sampleEnvelope() {
    Instant t = Instant.parse("2026-01-01T00:00:00Z");
    return new ExternalSignalEnvelope(
        "1.0",
        "m1",
        "s",
        "b",
        "c",
        "e",
        "st",
        null,
        t,
        t,
        "corr",
        null,
        new SignalSecurityContext("p", "s", "MOCK", t, t.plusSeconds(3600), "prof", null),
        new SignalCompletion(
            AdapterDispositionMode.COMPLETED,
            CanonicalOutcome.technical(TechnicalStatus.SUCCESS),
            List.of(),
            List.of()));
  }
}
