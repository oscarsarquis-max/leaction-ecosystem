package br.com.banco.spider.context.capability;

import java.util.List;
import java.util.Optional;

/** Catálogo canônico mínimo: capabilities do baseline e do primeiro plano composto. */
public final class StaticBusinessCapabilityCatalog implements BusinessCapabilityCatalog {

  private static final String INPUT_PREFIX = "spider-capability://input/";
  private static final String OUTPUT_PREFIX = "spider-capability://output/";

  private final List<BusinessCapability> capabilities =
      List.of(
          available(
              "CREDIT_RELEASE_DIAGNOSTIC",
              "Investigar a condição que impede a liberação de uma proposta de crédito.",
              route(
                  "CREDIT_RELEASE_DIAGNOSTIC_V1",
                  "mock-universal",
                  "RETRY_THEN_SUCCESS",
                  "RETRY_THEN_SUCCESS",
                  true)),
          unavailableWithRoute(
              "COLLECTION_DIAGNOSTIC",
              "Investigar uma cobrança pendente.",
              route(
                  "COLLECTION_DIAGNOSTIC_V1",
                  "mock-universal",
                  "SUCCESS_MULTI_STEP",
                  "SUCCESS_MULTI_STEP",
                  false)),
          unavailableWithRoute(
              "BILLING_DIAGNOSTIC",
              "Investigar uma falha de faturamento.",
              route(
                  "BILLING_DIAGNOSTIC_V1",
                  "mock-universal",
                  "SUCCESS_MULTI_STEP",
                  "SUCCESS_MULTI_STEP",
                  false)),
          unavailableWithRoute(
              "CUSTOMER_DATA_DIAGNOSTIC",
              "Identificar inconsistências cadastrais de um cliente.",
              route(
                  "CUSTOMER_DATA_DIAGNOSTIC_V1",
                  "mock-universal",
                  "SUCCESS_MULTI_STEP",
                  "SUCCESS_MULTI_STEP",
                  false)),
          unavailableWithRoute(
              "SERVICE_REQUEST_DIAGNOSTIC",
              "Investigar estado e bloqueios de uma solicitação de atendimento.",
              route(
                  "SERVICE_REQUEST_DIAGNOSTIC_V1",
                  "mock-universal",
                  "SUCCESS_MULTI_STEP",
                  "SUCCESS_MULTI_STEP",
                  false)),
          unavailableWithRoute(
              "INCIDENT_DIAGNOSTIC",
              "Investigar a condição atual de um incidente operacional.",
              route(
                  "INCIDENT_DIAGNOSTIC_V1",
                  "mock-universal",
                  "SUCCESS_MULTI_STEP",
                  "SUCCESS_MULTI_STEP",
                  false)),
          available(
              "IDENTIFY_CUSTOMER",
              "Identificar o cliente no contexto autenticado sem consultar sistema externo.",
              route(
                  "AUTHENTICATED_CONTEXT_CUSTOMER_V1",
                  "context-principal",
                  "IDENTIFY_CUSTOMER",
                  "CONTEXT_ONLY",
                  false)),
          unavailable(
              "GET_CUSTOMER_PROFILE", "Consultar o perfil empresarial consolidado do cliente."),
          unavailable(
              "CHECK_CUSTOMER_REGISTRATION", "Validar a situação cadastral necessária à análise."),
          unavailable("GET_CREDIT_PROFILE", "Consultar o perfil de crédito aplicável ao cliente."),
          unavailable(
              "FIND_ELIGIBLE_PRODUCTS", "Localizar produtos de capital de giro elegíveis."),
          unavailable(
              "SIMULATE_WORKING_CAPITAL",
              "Simular condições de capital de giro para o contexto econômico informado."),
          unavailable(
              "PRESENT_OPTIONS", "Apresentar opções elegíveis sem contratar ou mutar dados."));

  @Override
  public List<BusinessCapability> list() {
    return capabilities;
  }

  @Override
  public Optional<BusinessCapability> findById(String capabilityId) {
    return capabilities.stream()
        .filter(capability -> capability.capabilityId().equals(capabilityId))
        .findFirst();
  }

  private static BusinessCapability available(
      String capabilityId, String description, CapabilityRoute route) {
    return definition(
        capabilityId, description, CapabilityAvailability.AVAILABLE, List.of(route));
  }

  private static BusinessCapability unavailable(String capabilityId, String description) {
    return definition(capabilityId, description, CapabilityAvailability.NOT_AVAILABLE, List.of());
  }

  private static BusinessCapability unavailableWithRoute(
      String capabilityId, String description, CapabilityRoute route) {
    return definition(
        capabilityId, description, CapabilityAvailability.NOT_AVAILABLE, List.of(route));
  }

  private static BusinessCapability definition(
      String capabilityId,
      String description,
      CapabilityAvailability availability,
      List<CapabilityRoute> routes) {
    String slug = capabilityId.toLowerCase().replace('_', '-');
    return new BusinessCapability(
        capabilityId,
        "1.0",
        description,
        INPUT_PREFIX + slug + "/v1",
        OUTPUT_PREFIX + slug + "/v1",
        CapabilityMutationType.READ_ONLY,
        availability,
        routes);
  }

  private static CapabilityRoute route(
      String routeRef,
      String adapterRef,
      String targetOperation,
      String mockScenario,
      boolean executable) {
    return new CapabilityRoute(
        routeRef, adapterRef, targetOperation, mockScenario, executable);
  }
}
