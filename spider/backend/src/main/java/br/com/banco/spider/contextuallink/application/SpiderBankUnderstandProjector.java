package br.com.banco.spider.contextuallink.application;

import br.com.banco.spider.context.application.ContextDecisionRecord;
import br.com.banco.spider.context.application.PageContextFacts;
import br.com.banco.spider.context.capability.CapabilityResolution;
import br.com.banco.spider.context.capability.CapabilityResolutionStatus;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.domain.CropFailurePolicy;
import br.com.banco.spider.context.planning.ContextExecutionPlan;
import br.com.banco.spider.context.planning.ContextExecutionPlanStep;
import br.com.banco.spider.contextuallink.domain.ContextualLinkSession;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Projeção humana + envelope técnico. A superfície principal não mostra Intent/Guard/Route. */
public final class SpiderBankUnderstandProjector {

  private SpiderBankUnderstandProjector() {}

  public static Map<String, Object> project(
      String status,
      String objective,
      ContextualLinkSession session,
      PageContextFacts facts,
      boolean directEntry,
      ContextDecisionRecord decision,
      List<String> cropSources,
      String amount,
      String amountSource,
      boolean amountInvented) {
    IntentContract contract = decision == null ? null : decision.intentContract();
    String intent = contract == null ? null : contract.intent();
    String purpose = contract == null ? null : contract.entities().get("purpose");
    String economicContext =
        contract == null ? null : contract.entities().get(CropFailurePolicy.ENTITY);
    boolean cropFailure = CropFailurePolicy.CROP_FAILURE.equals(economicContext);
    Map<String, Object> human = new LinkedHashMap<>();
    human.put("headline", headline(status));
    human.put("objective", objective);
    human.put("understanding", understanding(status, cropFailure, directEntry, purpose));
    human.put("policy", policy(status));
    human.put(
        "missing",
        "NEED_AMOUNT".equals(status)
            ? Map.of("key", "amount", "question", "De quanto você precisa?")
            : null);
    human.put("cropFailureNoted", cropFailure);
    boolean showPath = "UNDERSTOOD".equals(status) && decision != null && decision.executionPlan() != null;
    human.put("path", showPath ? path(decision) : null);
    human.put("capabilities", showPath ? capabilities(decision) : List.of());

    Map<String, Object> technical = new LinkedHashMap<>();
    technical.put("status", status);
    technical.put("intent", intent);
    technical.put("domain", contract == null ? null : contract.domain());
    technical.put("purpose", purpose);
    technical.put("economicContext", cropFailure ? CropFailurePolicy.CROP_FAILURE : null);
    technical.put("economicContextSources", cropFailure ? cropSources : List.of());
    technical.put("amount", amount);
    technical.put("amountSource", amount == null ? null : amountSource);
    technical.put("amountInvented", amountInvented);
    technical.put("cropFailureFromLink", false);
    technical.put("confidence", contract == null ? null : contract.confidence());
    technical.put("decisionId", decision == null ? null : decision.decisionId());
    technical.put(
        "planId",
        decision == null || decision.executionPlan() == null
            ? null
            : decision.executionPlan().planId());
    technical.put(
        "planType",
        decision == null || decision.executionPlan() == null
            ? null
            : decision.executionPlan().planType());
    technical.put(
        "planStatus",
        decision == null || decision.executionPlan() == null
            ? null
            : decision.executionPlan().status() == null
                ? null
                : decision.executionPlan().status().name());
    technical.put("policyDecision", decision == null ? null : decision.guard().decision().name());
    technical.put("policyReason", decision == null ? null : decision.guard().reasonCode());
    technical.put("clickId", session == null ? null : session.click().clickId());
    technical.put("contextId", session == null ? null : session.click().contextId());
    technical.put("pageUsed", facts.present());
    technical.put("pageTitle", facts.present() ? facts.title() : null);
    technical.put("directEntry", directEntry);
    technical.put(
        "pageContext", directEntry ? "ABSENT" : facts.present() ? "CAPTURED" : "AUSENTE");
    technical.put("contextProvenance", directEntry ? "DIRECT_ENTRY" : "CONTEXTUAL_LINK");
    technical.put("intentProvenance", contract == null ? null : contract.provenance().source().name());
    technical.put("pageIsUntrustedData", true);
    technical.put("executionId", decision == null ? null : decision.executionId());

    Map<String, Object> body = new LinkedHashMap<>();
    body.put("status", status);
    body.put("human", human);
    body.put("technical", technical);
    body.put(
        "principle",
        "O Contextual Link fornece contexto de origem, mas não define a intenção. O objetivo pertence ao usuário. O Context Intelligence combina contexto permitido e objetivo declarado para produzir um Intent Contract governado. A partir dessa fronteira, Policy, Execution Plan e Capability Resolution permanecem determinísticos.");
    return body;
  }

  private static String headline(String status) {
    return switch (status) {
      case "NEED_AMOUNT", "UNDERSTOOD", "NEED_MORE" -> "O que o Spider entendeu";
      case "AMBIGUOUS" -> "Precisamos entender melhor";
      default -> "Não foi possível continuar com segurança";
    };
  }

  private static String understanding(
      String status, boolean cropFailure, boolean directEntry, String purpose) {
    if ("AMBIGUOUS".equals(status)) {
      return "Ainda não está claro o que você precisa resolver agora. Precisamos entender melhor.";
    }
    if ("UNSUPPORTED".equals(status) || "FAILED".equals(status)) {
      return "Este objetivo ainda não corresponde às situações que o Spider pode tratar com segurança.";
    }
    if (cropFailure) {
      return "Você precisa de recursos para atravessar este momento, honrar compromissos e preparar o próximo plantio. A reportagem sobre quebra de safra foi considerada como dado de origem — não como um pedido embutido no link.";
    }
    if ("PRODUCTION_CONTINUITY".equals(purpose) || "NEED_AMOUNT".equals(status) || "UNDERSTOOD".equals(status)) {
      if (directEntry) {
        return "Você precisa de recursos para manter a sua produção. Não identificamos quebra de safra neste pedido.";
      }
      return "Você precisa de recursos para manter a sua produção.";
    }
    return "Registramos o que você precisa resolver.";
  }

  private static String policy(String status) {
    return switch (status) {
      case "NEED_AMOUNT" ->
          "A política contextual permite continuar. Ainda precisamos de uma informação: de quanto você precisa.";
      case "UNDERSTOOD" ->
          "A política contextual aceitou este entendimento. O caminho está parcialmente disponível — sem contratar e sem executar.";
      case "AMBIGUOUS" -> "A política contextual não presume um caminho enquanto o objetivo não estiver claro.";
      default -> "A política contextual não autoriza avançar neste entendimento.";
    };
  }

  private static Map<String, Object> path(ContextDecisionRecord decision) {
    ContextExecutionPlan plan = decision.executionPlan();
    List<Map<String, Object>> steps = new ArrayList<>();
    for (ContextExecutionPlanStep step : plan.steps()) {
      CapabilityResolution resolved =
          decision.capabilities().stream()
              .filter(item -> step.capabilityId().equals(item.capabilityId()))
              .findFirst()
              .orElse(null);
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("name", capabilityName(step.capabilityId()));
      row.put("state", capabilityState(resolved));
      row.put("capabilityId", step.capabilityId());
      steps.add(row);
    }
    Map<String, Object> path = new LinkedHashMap<>();
    path.put("title", "Para ajudar você, o Spider precisa:");
    path.put("steps", steps);
    path.put("honest", "Nenhuma contratação, taxa, prazo ou desembolso acontece nesta demonstração.");
    return path;
  }

  private static List<Map<String, Object>> capabilities(ContextDecisionRecord decision) {
    List<Map<String, Object>> items = new ArrayList<>();
    for (CapabilityResolution item : decision.capabilities()) {
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("name", capabilityName(item.capabilityId()));
      row.put("state", capabilityState(item));
      row.put("capabilityId", item.capabilityId());
      items.add(row);
    }
    return items;
  }

  private static String capabilityState(CapabilityResolution item) {
    if (item == null) {
      return "necessário";
    }
    if (item.status() == CapabilityResolutionStatus.RESOLVED) {
      return "já resolvido";
    }
    return "ainda não disponível";
  }

  static String capabilityName(String capabilityId) {
    return switch (capabilityId) {
      case "IDENTIFY_CUSTOMER" -> "Identificar cliente";
      case "GET_CUSTOMER_PROFILE" -> "Consultar perfil do cliente";
      case "CHECK_CUSTOMER_REGISTRATION" -> "Verificar cadastro do cliente";
      case "GET_CREDIT_PROFILE" -> "Consultar perfil de crédito";
      case "FIND_ELIGIBLE_PRODUCTS" -> "Encontrar produtos elegíveis";
      case "SIMULATE_WORKING_CAPITAL" -> "Simular capital de giro";
      case "PRESENT_OPTIONS" -> "Apresentar opções";
      default -> capabilityId;
    };
  }
}
