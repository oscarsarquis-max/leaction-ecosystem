package br.com.banco.spider.satellite.application;

import br.com.banco.spider.context.capability.BusinessCapability;
import br.com.banco.spider.context.capability.CapabilityAvailability;
import br.com.banco.spider.context.capability.StaticBusinessCapabilityCatalog;
import br.com.banco.spider.context.planning.ContextExecutionPlanStep;
import br.com.banco.spider.context.planning.ExecutionPlanTemplate;
import br.com.banco.spider.context.planning.StaticExecutionPlanCatalog;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Projects the existing SEEK_WORKING_CAPITAL plan without executing steps or inventing results.
 * IDENTIFY_CUSTOMER stays incomplete unless an authenticated customer principal exists.
 */
public final class WorkingCapitalPlanProjection {

  public static final String IDENTIFY_CUSTOMER = "IDENTIFY_CUSTOMER";

  private WorkingCapitalPlanProjection() {}

  public static Map<String, Object> project() {
    return project(false);
  }

  public static Map<String, Object> project(boolean authenticatedCustomerPrincipal) {
    ExecutionPlanTemplate plan =
        new StaticExecutionPlanCatalog()
            .findByIntent(SatelliteContractV1.SEEK_WORKING_CAPITAL)
            .orElseThrow(() -> new IllegalStateException("Plano de capital de giro ausente."));
    StaticBusinessCapabilityCatalog capabilities = new StaticBusinessCapabilityCatalog();
    List<Map<String, Object>> steps = new ArrayList<>();
    List<Map<String, Object>> impediments = new ArrayList<>();
    for (ContextExecutionPlanStep step : plan.steps()) {
      BusinessCapability capability =
          capabilities.findById(step.capabilityId()).orElse(null);
      CapabilityAvailability availability =
          capability == null ? CapabilityAvailability.NOT_AVAILABLE : capability.availability();
      boolean completed = IDENTIFY_CUSTOMER.equals(step.capabilityId()) && authenticatedCustomerPrincipal;
      String reason = impedimentReason(step.capabilityId(), availability, authenticatedCustomerPrincipal);
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("sequence", step.sequence());
      row.put("stepId", step.stepId());
      row.put("capabilityId", step.capabilityId());
      row.put("required", step.required());
      row.put("availability", availability.name());
      row.put("completed", completed);
      row.put("reason", reason);
      steps.add(row);
      if (!completed) {
        Map<String, Object> impediment = new LinkedHashMap<>();
        impediment.put("sequence", step.sequence());
        impediment.put("capabilityId", step.capabilityId());
        impediment.put("availability", availability.name());
        impediment.put("reason", reason);
        impediments.add(impediment);
      }
    }
    Map<String, Object> summary = new LinkedHashMap<>();
    summary.put("kind", "WORKING_CAPITAL_PLAN_IMPEDIMENTS");
    summary.put("intent", SatelliteContractV1.SEEK_WORKING_CAPITAL);
    summary.put("planId", plan.planType());
    summary.put("analysisComplete", false);
    summary.put("providerDispatched", false);
    summary.put("authenticatedCustomerPrincipal", authenticatedCustomerPrincipal);
    summary.put("steps", steps);
    summary.put("impediments", impediments);
    return summary;
  }

  private static String impedimentReason(
      String capabilityId, CapabilityAvailability availability, boolean authenticatedCustomerPrincipal) {
    if (IDENTIFY_CUSTOMER.equals(capabilityId) && !authenticatedCustomerPrincipal) {
      return "IDENTIFY_CUSTOMER só se conclui com contexto autenticado do cliente. A identidade técnica do satélite não identifica o cliente.";
    }
    if (availability == CapabilityAvailability.NOT_AVAILABLE) {
      return "Capability " + capabilityId + " permanece indisponível neste ambiente. A análise não pode avançar por este passo.";
    }
    return "O passo " + capabilityId + " não foi executado nesta jornada.";
  }
}
