package br.com.spiderbank.application;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class SubmitWorkingCapitalJourneyUseCase {

  private final SpiderDecisionGateway gateway;
  private final InMemoryJourneyStore store;
  private final DemoCustomerSessionService sessions;

  public SubmitWorkingCapitalJourneyUseCase(SpiderDecisionGateway gateway, InMemoryJourneyStore store) {
    this(gateway, store, null);
  }

  @Autowired
  public SubmitWorkingCapitalJourneyUseCase(
      SpiderDecisionGateway gateway, InMemoryJourneyStore store, DemoCustomerSessionService sessions) {
    this.gateway = gateway;
    this.store = store;
    this.sessions = sessions;
  }

  public Map<String, Object> execute(boolean objectiveConfirmed, String correlationId, String idempotencyKey) {
    return execute(objectiveConfirmed, correlationId, idempotencyKey, null, null, null);
  }

  public Map<String, Object> execute(
      boolean objectiveConfirmed,
      String correlationId,
      String idempotencyKey,
      String sessionAssertion,
      Long principalCents,
      Integer termMonths) {
    if (!objectiveConfirmed) {
      throw new CreditJourneyException(
          "OBJECTIVE_NOT_CONFIRMED",
          400,
          "Confirme explicitamente o objetivo de buscar capital de giro antes de enviar a interação.");
    }
    String correlation = normalizeId(correlationId, "correlationId");
    String idempotency = normalizeId(idempotencyKey, "idempotencyKey");
    String assertion = sessions == null ? sessionAssertion : sessions.requireAssertion(sessionAssertion);
    Map<String, Object> extensions = new java.util.LinkedHashMap<>();
    if (assertion != null) {
      extensions.put("customerAssertion", assertion);
    }
    if (principalCents != null && (principalCents < 10000 || principalCents > 100000000)) {
      throw new CreditJourneyException(
          "VALIDATION_ERROR", 400, "Valor declarado está fora da faixa demonstrativa.");
    }
    if (termMonths != null && (termMonths < 1 || termMonths > 36)) {
      throw new CreditJourneyException(
          "VALIDATION_ERROR", 400, "Prazo declarado está fora da faixa demonstrativa.");
    }
    if (principalCents != null || termMonths != null) {
      Map<String, Object> parameters = new java.util.LinkedHashMap<>();
      if (principalCents != null) {
        parameters.put("principalCents", principalCents);
      }
      if (termMonths != null) {
        parameters.put("termMonths", termMonths);
      }
      parameters.put("origin", "USER_DECLARED");
      extensions.put("workingCapitalParameters", parameters);
    }
    String fingerprint =
        GovernedCreditContext.OBJECTIVE
            + "|"
            + GovernedCreditContext.SOURCE_ID
            + "|"
            + (assertion == null ? "" : assertion)
            + "|"
            + principalCents
            + "|"
            + termMonths;
    Map<String, Object> existing = store.get(idempotency);
    if (existing != null) {
      if (!fingerprint.equals(store.fingerprint(idempotency))) {
        throw new CreditJourneyException(
            "IDEMPOTENCY_CONFLICT", 409, "A mesma chave já foi usada com outro pedido.");
      }
      return existing;
    }
    String declaredAt = Instant.now().toString();
    SpiderDecisionGateway.Result result =
        gateway.submit(
            new SpiderDecisionGateway.Command(
                correlation,
                idempotency,
                "msg-" + UUID.randomUUID(),
                declaredAt,
                GovernedCreditContext.attributes(),
                extensions));
    if (result.kind() == SpiderDecisionGateway.Kind.SPIDER_UNAVAILABLE) {
      throw new CreditJourneyException(result.errorCode(), result.httpStatus(), result.message(), true);
    }
    if (result.kind() == SpiderDecisionGateway.Kind.INTEGRATION_FAILURE) {
      throw new CreditJourneyException(result.errorCode(), result.httpStatus(), result.message());
    }
    if (result.kind() == SpiderDecisionGateway.Kind.CLIENT_ERROR) {
      throw new CreditJourneyException(result.errorCode(), result.httpStatus(), result.message());
    }
    Map<String, Object> view = CreditJourneyMapper.fromSatelliteResponse(result.body(), correlation);
    store.put(idempotency, fingerprint, view);
    return view;
  }

  private static String normalizeId(String value, String field) {
    if (value == null || value.isBlank()) {
      throw new CreditJourneyException("VALIDATION_ERROR", 400, field + " obrigatório.");
    }
    if (value.length() < 8 || value.length() > 80) {
      throw new CreditJourneyException("VALIDATION_ERROR", 400, field + " inválido.");
    }
    return value;
  }
}
