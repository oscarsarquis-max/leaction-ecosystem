package br.com.spiderbank.application;

import java.util.LinkedHashMap;
import java.util.Map;

/** Server-registered synthetic credit context. Not a customer or credit profile. */
public final class GovernedCreditContext {

  public static final String SOURCE_ID = "SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1";
  public static final String PURPOSE = "WORKING_CAPITAL_ASSESSMENT";
  public static final String OBJECTIVE = "SEEK_WORKING_CAPITAL";
  public static final String CHANNEL = "SPIDERBANK_PUBLIC_DEMO";
  public static final String PURPOSE_VERSION = "demo-working-capital-v1";
  public static final String THEME = "working_capital";
  public static final String SITUATION = "synthetic_working_capital_need";
  public static final String NEED = "assess_working_capital";
  public static final String HORIZON = "months";

  private GovernedCreditContext() {}

  public static Map<String, Object> publicView() {
    Map<String, Object> view = new LinkedHashMap<>();
    view.put("environment", "MOCK_ONLY");
    view.put("synthetic", true);
    view.put("title", "Situação demonstrativa de capital de giro");
    view.put(
        "summary",
        "Uma empresa ilustrativa declara necessidade temporária de caixa para manter operação e atender pedidos. Os dados são sintéticos, registrados no servidor e não descrevem uma pessoa, uma empresa real nem um perfil de crédito.");
    view.put("originLabel", "Fonte governada do SpiderBank");
    view.put("originDetail", "Registro no servidor da Spider, com proveniência SATELLITE_GOVERNED.");
    view.put("sourceId", SOURCE_ID);
    view.put("captureMethod", "SERVER_REGISTRY");
    view.put("trustLevel", "GOVERNED");
    view.put("classification", "INTERNAL");
    view.put("nonPersonal", true);
    view.put("objectiveLabel", "Buscar capital de giro");
    view.put("objectiveCode", OBJECTIVE);
    view.put(
        "objectiveHelp",
        "A confirmação envia esta declaração reconhecida à Spider. O SpiderBank não escolhe o plano nem o Intent canônico.");
    view.put(
        "limits",
        "Esta fonte não substitui cadastro, perfil de crédito, elegibilidade, simulação ou contratação.");
    return view;
  }

  public static Map<String, String> attributes() {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", CHANNEL);
    attributes.put("purposeVersion", PURPOSE_VERSION);
    attributes.put("theme", THEME);
    attributes.put("situation", SITUATION);
    attributes.put("need", NEED);
    attributes.put("horizon", HORIZON);
    return attributes;
  }
}
