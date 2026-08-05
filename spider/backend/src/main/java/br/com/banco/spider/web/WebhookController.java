package br.com.banco.spider.web;

import br.com.banco.spider.repository.AuditTraceRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@RestController
@RequestMapping("/api/v1/webhooks")
@Tag(name = "Webhooks")
public class WebhookController {

  private static final Logger log = LoggerFactory.getLogger(WebhookController.class);

  private final AuditTraceRepository auditTraceRepository;

  public WebhookController(AuditTraceRepository auditTraceRepository) {
    this.auditTraceRepository = auditTraceRepository;
  }

  @PostMapping("/callback/{correlationId}")
  @ResponseStatus(HttpStatus.ACCEPTED)
  @Operation(summary = "Callback assíncrono de sistema legado")
  public Mono<Map<String, Object>> callback(
      @PathVariable UUID correlationId, @RequestBody Map<String, Object> body) {
    log.info("Webhook callback correlationId={} bodyKeys={}", correlationId, body.keySet());
    return Mono.fromCallable(
            () -> {
              auditTraceRepository
                  .findByCorrelationId(correlationId)
                  .forEach(
                      t -> {
                        t.setMetadata("{\"callback\":true}");
                        auditTraceRepository.save(t);
                      });
              return Map.<String, Object>of(
                  "accepted", true, "correlationId", correlationId.toString());
            })
        .subscribeOn(Schedulers.boundedElastic());
  }
}
