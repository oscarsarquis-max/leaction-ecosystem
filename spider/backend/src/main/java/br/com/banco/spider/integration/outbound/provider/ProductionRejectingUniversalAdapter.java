package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import br.com.banco.spider.integration.port.UniversalAdapterRequest;
import br.com.banco.spider.integration.port.UniversalAdapterResult;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

/**
 * A porta universal não executa demo nem efeito financeiro em produção. O recorte
 * LIST_EXTERNAL_PAYMENTS usa o adapter do ActionHub Pay, não esta porta.
 */
@Component
@Profile("production")
public class ProductionRejectingUniversalAdapter implements UniversalAdapterPort {

  @Override
  public Mono<UniversalAdapterResult> invoke(UniversalAdapterRequest request) {
    Instant now = Instant.now();
    String correlation =
        request.trace() == null || request.trace().correlationId() == null
            ? ""
            : request.trace().correlationId();
    return Mono.just(
        UniversalAdapterResult.builder()
            .invocationId(request.invocationId())
            .executionId(request.executionId())
            .stepId(request.stepId())
            .attemptId(request.attemptId())
            .startedAt(now)
            .completedAt(now)
            .dispositionMode(AdapterDispositionMode.REJECTED)
            .outcome(CanonicalOutcome.technical(TechnicalStatus.FAILURE))
            .correlationId(correlation)
            .errors(
                List.of(
                    CanonicalError.builder()
                        .errorId("err-" + UUID.randomUUID())
                        .code("PRODUCTION_UNIVERSAL_ADAPTER_DISABLED")
                        .category(ErrorCategory.UNAVAILABLE)
                        .severity(ErrorSeverity.ERROR)
                        .message("A porta universal não executa operações neste recorte produtivo.")
                        .retryable(false)
                        .occurredAt(now)
                        .source(
                            new CanonicalError.ErrorSource(
                                "adapter", request.stepId(), "production-rejecting-adapter", request.bindingRef()))
                        .build()))
            .build());
  }
}
