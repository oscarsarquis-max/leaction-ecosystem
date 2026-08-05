package br.com.banco.spider.web.controller;

import br.com.banco.spider.domain.OrchestrationOutcome;
import br.com.banco.spider.domain.ProductOrchestrateRequest;
import br.com.banco.spider.orchestrator.OrchestrationService;
import br.com.banco.spider.web.filter.TraceContextWebFilter;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/v1/products")
@Tag(name = "Product Orchestrator")
public class ProductOrchestratorController {

  private final OrchestrationService orchestrationService;

  public ProductOrchestratorController(OrchestrationService orchestrationService) {
    this.orchestrationService = orchestrationService;
  }

  @PostMapping(
      value = "/orchestrate",
      consumes = MediaType.APPLICATION_JSON_VALUE,
      produces = MediaType.APPLICATION_PROBLEM_JSON_VALUE)
  @Operation(summary = "Orquestra intenção de produto (originador → legado → JWT → callback)")
  public Mono<ProblemDetail> orchestrate(
      @Valid @RequestBody ProductOrchestrateRequest request, ServerWebExchange exchange) {
    String headerTp =
        exchange.getRequest().getHeaders().getFirst(TraceContextWebFilter.TRACEPARENT_HEADER);

    return Mono.deferContextual(
            ctx -> {
              String traceparent =
                  ctx.getOrDefault(
                      TraceContextWebFilter.CONTEXT_KEY,
                      headerTp != null ? headerTp : TraceContextWebFilter.generateTraceparent());
              return orchestrationService.orchestrate(request, traceparent);
            })
        .map(this::toProblemDetail);
  }

  private ProblemDetail toProblemDetail(OrchestrationOutcome outcome) {
    boolean ok = outcome.legacyHttpStatus() >= 200 && outcome.legacyHttpStatus() < 300;
    ProblemDetail problem =
        ProblemDetail.forStatus(ok ? HttpStatus.OK : HttpStatus.BAD_GATEWAY);
    problem.setType(URI.create("https://spider.leaction.local/problems/orchestration"));
    problem.setTitle(ok ? "Orchestration completed" : "Orchestration failed at legacy");
    problem.setDetail(
        ok
            ? "Chamada ao legado financeiro concluída; JWT de transição emitido e callback disparado."
            : "Falha ao processar no service-legado-financeiro.");
    problem.setProperty("traceparent", outcome.traceparent());
    problem.setProperty("productId", outcome.productId());
    problem.setProperty("transactionId", outcome.transactionId());
    problem.setProperty("status_tecnico", outcome.technicalStatus());
    problem.setProperty("legacyHttpStatus", outcome.legacyHttpStatus());
    problem.setProperty("latencyMs", outcome.latencyMs());
    problem.setProperty("stateTransitionToken", outcome.stateTransitionToken());
    problem.setProperty("legacyBody", outcome.legacyBody());
    return problem;
  }
}
