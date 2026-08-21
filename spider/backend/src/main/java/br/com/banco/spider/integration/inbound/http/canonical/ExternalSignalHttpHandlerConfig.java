package br.com.banco.spider.integration.inbound.http.canonical;

import br.com.banco.spider.execution.signal.ExternalSignalApplicationPort;
import br.com.banco.spider.execution.signal.ExternalSignalEnvelope;
import br.com.banco.spider.execution.signal.ExternalSignalIngressOutcome;
import br.com.banco.spider.execution.signal.ExternalSignalIngressResult;
import br.com.banco.spider.execution.signal.ExternalSignalIngressUseCase;
import br.com.banco.spider.execution.signal.ExternalSignalProcessingResult;
import br.com.banco.spider.execution.signal.ExternalSignalProcessingStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import reactor.core.publisher.Mono;

@Configuration
@ConditionalOnProperty(name = "spider.canonical.signal-http.enabled", havingValue = "true")
public class ExternalSignalHttpHandlerConfig {

  private static final Logger log = LoggerFactory.getLogger(ExternalSignalHttpHandlerConfig.class);

  @Bean
  @Primary
  ExternalSignalHttpApplicationPort externalSignalHttpApplicationPort(
      ExternalSignalApplicationPort inline,
      ExternalSignalIngressUseCase ingress,
      @Value("${spider.signal.ingress.durable-application.enabled:false}") boolean durable) {
    if (durable) {
      log.info("event=signal_http_handler_type reasonCode=DURABLE");
      return envelope ->
          ingress
              .ingest(envelope)
              .map(ExternalSignalHttpHandlerConfig::toProcessingResult);
    }
    log.info("event=signal_http_handler_type reasonCode=INLINE");
    return inline::process;
  }

  private static ExternalSignalProcessingResult toProcessingResult(ExternalSignalIngressResult r) {
    ExternalSignalProcessingStatus status =
        switch (r.outcome()) {
          case ACCEPTED_PENDING_APPLICATION, DUPLICATE_ALREADY_ACCEPTED, DUPLICATE_ALREADY_APPLIED ->
              ExternalSignalProcessingStatus.DUPLICATE;
          case APPLIED_INLINE ->
              r.legacyResult() != null
                  ? r.legacyResult().processingStatus()
                  : ExternalSignalProcessingStatus.ACCEPTED_AND_RESUMED;
          case LATE -> ExternalSignalProcessingStatus.LATE_REJECTED;
          case ORPHAN -> ExternalSignalProcessingStatus.ORPHANED;
          case REPLAY_CONFLICT -> ExternalSignalProcessingStatus.CONFLICT;
          default -> ExternalSignalProcessingStatus.REJECTED;
        };
    // ACCEPTED_PENDING maps to a non-resume status that HTTP can treat as 202-like accepted
    if (r.outcome() == ExternalSignalIngressOutcome.ACCEPTED_PENDING_APPLICATION) {
      status = ExternalSignalProcessingStatus.ACCEPTED_AND_TERMINATED;
    }
    if (r.legacyResult() != null) {
      return r.legacyResult();
    }
    return ExternalSignalProcessingResult.of(status, null, null, null, null, null);
  }
}
