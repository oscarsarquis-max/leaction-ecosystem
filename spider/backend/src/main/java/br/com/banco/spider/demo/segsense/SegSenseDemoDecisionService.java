package br.com.banco.spider.demo.segsense;

import br.com.banco.spider.satellite.application.SatelliteInteractionService;
import java.util.Map;
import reactor.core.publisher.Mono;

/** Deprecated HTTP slice. Delegates to Satellite Contract V1. No second decision engine. */
public final class SegSenseDemoDecisionService {

  static final String CONTRACT_VERSION = "segsense-demo-contract-v1";
  static final String SCENARIO = "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1";
  static final String ALLOWED_OBJECTIVE = "UNDERSTAND_FAMILY_PROTECTION_OPTIONS";
  static final String WATERMARK =
      "DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO";
  static final String SPIDER_PATH = "SATELLITE_CONTRACT_V1_THEN_CAPABILITY_RESOLUTION";

  private final SatelliteInteractionService satellite;

  public SegSenseDemoDecisionService(SatelliteInteractionService satellite) {
    this.satellite = satellite;
  }

  public Mono<Decision> decide(Command command) {
    if (command == null) {
      return Mono.just(Decision.invalid("Pedido vazio."));
    }
    if (!CONTRACT_VERSION.equals(command.contractVersion())) {
      return Mono.just(Decision.invalid("Versão de contrato de demonstração inválida."));
    }
    if (!"SEGSENSE".equals(command.applicationId())) {
      return Mono.just(Decision.invalid("Identidade de aplicação não autorizada nesta fatia."));
    }
    if (!SCENARIO.equals(command.scenarioKey())) {
      return Mono.just(Decision.invalid("Cenário sintético desconhecido."));
    }
    return satellite
        .interact(DemoToSatelliteMapper.SATELLITE_ID, DemoToSatelliteMapper.toRequest(command))
        .map(DemoToSatelliteMapper::toLegacy);
  }

  public record Command(
      String contractVersion,
      String applicationId,
      String scenarioKey,
      SegSenseDemoOriginSnapshot originSnapshot,
      String declaredObjective,
      String correlationId,
      String idempotencyKey) {}

  public record Decision(int status, String errorCode, String message, Map<String, Object> body) {
    static Decision ok(Map<String, Object> body) {
      return new Decision(200, null, null, body);
    }

    static Decision invalid(String message) {
      return new Decision(400, "VALIDATION_ERROR", message, null);
    }

    static Decision conflict() {
      return new Decision(409, "IDEMPOTENCY_CONFLICT", "A mesma chave já foi usada com outro pedido.", null);
    }
  }
}
