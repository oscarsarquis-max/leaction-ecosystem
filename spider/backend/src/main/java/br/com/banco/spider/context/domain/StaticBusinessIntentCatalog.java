package br.com.banco.spider.context.domain;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

public final class StaticBusinessIntentCatalog implements BusinessIntentCatalog {

  private final List<BusinessIntentDefinition> definitions =
      List.of(
          definition(
              "CREDIT",
              "Crédito",
              "INVESTIGATE_CREDIT_RELEASE",
              "IDENTIFY_BLOCKING_CONDITION",
              "Investigar liberação de proposta",
              "Entender por que uma proposta de crédito não foi liberada.",
              "proposalId",
              "DEMO-PROPOSAL-001"),
          definition(
              "COLLECTION",
              "Cobrança",
              "INVESTIGATE_COLLECTION_PENDING",
              "IDENTIFY_PENDING_COLLECTION_CONDITION",
              "Investigar cobrança pendente",
              "Entender por que uma cobrança continua pendente.",
              "collectionId",
              "DEMO-COLLECTION-001"),
          definition(
              "BILLING",
              "Faturamento",
              "INVESTIGATE_BILLING_FAILURE",
              "IDENTIFY_BILLING_FAILURE",
              "Investigar falha de faturamento",
              "Analisar uma falha no processamento de faturamento.",
              "invoiceId",
              "DEMO-INVOICE-001"),
          definition(
              "CUSTOMER_DATA",
              "Dados do cliente",
              "CHECK_CUSTOMER_DATA_INCONSISTENCY",
              "IDENTIFY_CUSTOMER_DATA_INCONSISTENCY",
              "Verificar inconsistência cadastral",
              "Identificar divergências nos dados de um cliente.",
              "customerId",
              "DEMO-CUSTOMER-001"),
          definition(
              "CUSTOMER_SERVICE",
              "Atendimento",
              "INVESTIGATE_SERVICE_REQUEST",
              "IDENTIFY_SERVICE_REQUEST_STATUS",
              "Investigar solicitação de atendimento",
              "Compreender o estado e os bloqueios de uma solicitação.",
              "serviceRequestId",
              "DEMO-SERVICE-REQUEST-001"),
          definition(
              "INCIDENT",
              "Incidente",
              "INVESTIGATE_INCIDENT",
              "IDENTIFY_INCIDENT_CONDITION",
              "Investigar incidente operacional",
              "Compreender a condição atual de um incidente.",
              "incidentId",
              "DEMO-INCIDENT-001"),
          new BusinessIntentDefinition(
              "CREDIT",
              "Crédito",
              "SEEK_WORKING_CAPITAL",
              "ASSESS_WORKING_CAPITAL_OPTIONS",
              "Buscar capital de giro",
              "Compreender opções de capital de giro para uma finalidade econômica declarada.",
              Set.of("purpose", "amount", "businessSituation"),
              Set.of("purpose"),
              Map.of(),
              false));

  private static BusinessIntentDefinition definition(
      String domain,
      String domainLabel,
      String intent,
      String objective,
      String title,
      String description,
      String entityKey,
      String entityValue) {
    return new BusinessIntentDefinition(
        domain,
        domainLabel,
        intent,
        objective,
        title,
        description,
        Set.of(entityKey),
        Set.of(entityKey),
        Map.of(entityKey, entityValue),
        true);
  }

  @Override
  public List<BusinessIntentDefinition> list() {
    return definitions;
  }

  @Override
  public Optional<BusinessIntentDefinition> findByIntent(String intent) {
    return definitions.stream().filter(item -> item.intent().equals(intent)).findFirst();
  }
}
