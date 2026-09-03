package br.com.banco.spider.context.planning;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/** Catálogo fechado que compõe intents em capabilities empresariais. */
public final class StaticExecutionPlanCatalog implements ExecutionPlanCatalog {

  private final List<ExecutionPlanTemplate> templates =
      List.of(
          single(
              "CREDIT_RELEASE_INVESTIGATION_PLAN_V1",
              "INVESTIGATE_CREDIT_RELEASE",
              "CREDIT_RELEASE_DIAGNOSTIC",
              "Identificar a condição que bloqueia a liberação do crédito."),
          single(
              "COLLECTION_INVESTIGATION_PLAN_V1",
              "INVESTIGATE_COLLECTION_PENDING",
              "COLLECTION_DIAGNOSTIC",
              "Identificar por que a cobrança permanece pendente."),
          single(
              "BILLING_INVESTIGATION_PLAN_V1",
              "INVESTIGATE_BILLING_FAILURE",
              "BILLING_DIAGNOSTIC",
              "Identificar a causa da falha de faturamento."),
          single(
              "CUSTOMER_DATA_CHECK_PLAN_V1",
              "CHECK_CUSTOMER_DATA_INCONSISTENCY",
              "CUSTOMER_DATA_DIAGNOSTIC",
              "Identificar divergências nos dados do cliente."),
          single(
              "SERVICE_REQUEST_INVESTIGATION_PLAN_V1",
              "INVESTIGATE_SERVICE_REQUEST",
              "SERVICE_REQUEST_DIAGNOSTIC",
              "Identificar estado e bloqueios da solicitação."),
          single(
              "INCIDENT_INVESTIGATION_PLAN_V1",
              "INVESTIGATE_INCIDENT",
              "INCIDENT_DIAGNOSTIC",
              "Identificar a condição atual do incidente."),
          workingCapital());

  @Override
  public List<ExecutionPlanTemplate> list() {
    return templates;
  }

  @Override
  public Optional<ExecutionPlanTemplate> findByIntent(String intent) {
    return templates.stream().filter(template -> template.intent().equals(intent)).findFirst();
  }

  private static ExecutionPlanTemplate single(
      String planType, String intent, String capabilityId, String reason) {
    return new ExecutionPlanTemplate(
        planType,
        intent,
        List.of(
            new ContextExecutionPlanStep(
                planType.toLowerCase() + "-01", 1, capabilityId, true, reason, null)));
  }

  private static ExecutionPlanTemplate workingCapital() {
    List<ContextExecutionPlanStep> steps = new ArrayList<>();
    add(steps, "IDENTIFY_CUSTOMER", "Identificar o cliente no contexto autenticado.");
    add(steps, "GET_CUSTOMER_PROFILE", "Compreender o perfil empresarial do cliente.");
    add(
        steps,
        "CHECK_CUSTOMER_REGISTRATION",
        "Validar se a situação cadastral permite continuar a análise.");
    add(steps, "GET_CREDIT_PROFILE", "Compreender o perfil de crédito aplicável.");
    add(
        steps,
        "FIND_ELIGIBLE_PRODUCTS",
        "Localizar produtos compatíveis com o contexto econômico.");
    add(
        steps,
        "SIMULATE_WORKING_CAPITAL",
        "Simular condições sem contratar ou alterar dados.");
    add(steps, "PRESENT_OPTIONS", "Apresentar somente opções elegíveis e explicáveis.");
    return new ExecutionPlanTemplate(
        "WORKING_CAPITAL_DIAGNOSTIC_V1", "SEEK_WORKING_CAPITAL", steps);
  }

  private static void add(
      List<ContextExecutionPlanStep> steps, String capabilityId, String reason) {
    int sequence = steps.size() + 1;
    steps.add(
        new ContextExecutionPlanStep(
            "working-capital-%02d-%s".formatted(
                sequence, capabilityId.toLowerCase().replace('_', '-')),
            sequence,
            capabilityId,
            true,
            reason,
            null));
  }
}
