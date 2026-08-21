package br.com.banco.spider.execution.application;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.validation.CanonicalStructuralValidator;
import br.com.banco.spider.canonical.validation.OperationClass;
import br.com.banco.spider.canonical.validation.ValidationOutcome;
import br.com.banco.spider.domain.OrchestrationOutcome;
import br.com.banco.spider.domain.ProductOrchestrateRequest;
import br.com.banco.spider.integration.mapping.ProductOrchestrateCanonicalMapper;
import br.com.banco.spider.orchestrator.OrchestrationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/**
 * Ponte de compatibilidade: valida envelope canônico e delega ao fluxo legacy baseline.
 * Não duplica efeito externo; caminho canônico completo fica para incremento posterior.
 */
@Service
public class OrchestrationCompatibilityService {

  private static final Logger log = LoggerFactory.getLogger(OrchestrationCompatibilityService.class);

  public static final String PATH_LEGACY_BASELINE = "legacy_baseline";
  public static final String PATH_CANONICAL_FOUNDATION = "canonical_foundation";

  private final ProductOrchestrateCanonicalMapper mapper;
  private final CanonicalStructuralValidator validator;
  private final OrchestrationService orchestrationService;

  public OrchestrationCompatibilityService(
      ProductOrchestrateCanonicalMapper mapper,
      CanonicalStructuralValidator validator,
      OrchestrationService orchestrationService) {
    this.mapper = mapper;
    this.validator = validator;
    this.orchestrationService = orchestrationService;
  }

  public Mono<OrchestrationOutcome> orchestrate(
      ProductOrchestrateRequest request, String traceparent) {
    CanonicalExecutionRequest canonical = mapper.toCanonical(request, traceparent);
    ValidationOutcome validation =
        validator.validateRequest(canonical, OperationClass.EFFECT);

    if (validation.hasBlockingErrors()) {
      log.warn(
          "execution_path={} canonical_validation=rejected errors={} executionId={}",
          PATH_CANONICAL_FOUNDATION,
          validation.errors().size(),
          canonical.execution().executionId());
      // Incremento 001: não quebra o contrato HTTP atual — segue baseline legado
      // após registrar a rejeição canônica como evidência de migração.
    } else {
      log.info(
          "execution_path={} secondary={} canonical_validation=ok executionId={} correlationId={}",
          PATH_LEGACY_BASELINE,
          PATH_CANONICAL_FOUNDATION,
          canonical.execution().executionId(),
          canonical.trace().correlationId());
    }

    return orchestrationService.orchestrate(request, traceparent);
  }
}
