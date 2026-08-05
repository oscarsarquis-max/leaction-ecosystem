package br.com.banco.spider.web;

import br.com.banco.spider.model.AuditTrace;
import br.com.banco.spider.model.ProductRoute;
import br.com.banco.spider.repository.AuditTraceRepository;
import br.com.banco.spider.repository.ProductRouteRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

/** Endpoints operacionais do painel (consulta técnica). */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Ops")
public class OrchestratorController {

  private final ProductRouteRepository productRouteRepository;
  private final AuditTraceRepository auditTraceRepository;

  public OrchestratorController(
      ProductRouteRepository productRouteRepository, AuditTraceRepository auditTraceRepository) {
    this.productRouteRepository = productRouteRepository;
    this.auditTraceRepository = auditTraceRepository;
  }

  @GetMapping("/routes")
  @Operation(summary = "Lista rotas de produto (tb_product_routes)")
  public Mono<List<ProductRoute>> routes() {
    return Mono.fromCallable(productRouteRepository::findByEnabledTrueOrderByProductCodeAscVersionDesc)
        .subscribeOn(Schedulers.boundedElastic());
  }

  @GetMapping("/traces/recent")
  @Operation(summary = "Últimos traces (tb_audit_trace)")
  public Mono<List<AuditTrace>> recentTraces() {
    return Mono.fromCallable(auditTraceRepository::findTop50ByOrderByStartedAtDesc)
        .subscribeOn(Schedulers.boundedElastic());
  }
}
