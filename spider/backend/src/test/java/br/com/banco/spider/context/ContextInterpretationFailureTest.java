package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import br.com.banco.spider.config.ContextIntelligenceProperties;
import br.com.banco.spider.context.application.ContextInputRedactor;
import br.com.banco.spider.context.application.ContextInterpretationService;
import br.com.banco.spider.context.application.ContextInterpreterPrompt;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider;
import br.com.banco.spider.context.domain.StaticBusinessIntentCatalog;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;

class ContextInterpretationFailureTest {

  @Test
  void providerUnavailableFailsClosedWithoutContextPlaneFailure() {
    var result = service(null, Duration.ofMillis(20)).interpret("objetivo", "principal").block();
    assertEquals(
        ContextInterpretationService.InterpretationStatus.PROVIDER_UNAVAILABLE,
        result.status());
    assertEquals(ContextInterpretationService.AiState.UNAVAILABLE, result.aiState());
  }

  @Test
  void timeoutFailsClosed() {
    ContextInterpretationProvider provider =
        provider(Mono.never());
    var result =
        service(provider, Duration.ofMillis(10))
            .interpret("objetivo", "principal")
            .block(Duration.ofSeconds(1));
    assertEquals(ContextInterpretationService.InterpretationStatus.TIMEOUT, result.status());
    assertEquals(null, result.decision());
  }

  @Test
  void unknownIntentFromProviderIsRejectedBeforeGuardAndRouter() {
    ContextInterpretationProvider provider =
        provider(
            Mono.just(
                new ContextInterpretationProvider.ProviderResult(
                    ContextInterpretationProvider.ProviderStatus.MATCHED,
                    "TRANSFER_MONEY_NOW",
                    Map.of(),
                    List.of(),
                    new BigDecimal("0.99"),
                    ContextInterpretationProvider.Usage.empty(),
                    3)));
    var result =
        service(provider, Duration.ofMillis(100))
            .interpret("transfira agora", "principal")
            .block();
    assertEquals(
        ContextInterpretationService.InterpretationStatus.INVALID_RESPONSE,
        result.status());
    assertEquals(null, result.decision());
  }

  private static ContextInterpretationService service(
      ContextInterpretationProvider provider, Duration timeout) {
    ContextIntelligenceProperties properties = new ContextIntelligenceProperties();
    properties.getAi().setEnabled(true);
    properties.getAi().setTimeout(timeout);
    IdentifierGenerator ids = mock(IdentifierGenerator.class);
    when(ids.nextId("ctxi")).thenReturn("ctxi-test");
    SpiderClock clock = mock(SpiderClock.class);
    when(clock.now()).thenReturn(Instant.parse("2026-09-03T16:00:00Z"));
    return new ContextInterpretationService(
        properties,
        provider,
        new ContextInterpreterPrompt(ContextInterpreterPrompt.VERSION, "structured only"),
        new ContextInputRedactor(2000),
        new StaticBusinessIntentCatalog(),
        null,
        mock(OperationalEventPublisher.class),
        ids,
        clock);
  }

  private static ContextInterpretationProvider provider(
      Mono<ContextInterpretationProvider.ProviderResult> response) {
    return new ContextInterpretationProvider() {
      @Override
      public String providerId() {
        return "fake";
      }

      @Override
      public String modelId() {
        return "fake-model";
      }

      @Override
      public Mono<ProviderResult> interpret(ProviderRequest request) {
        return response;
      }
    };
  }
}
