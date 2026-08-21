package br.com.banco.spider.execution.callback;

import java.util.List;

public record CallbackAuthorizationRequest(
    CallbackDefinition callbackDefinition,
    String ownerPrincipalRef,
    String originatorId,
    String executionState,
    String technicalStatus,
    List<String> dataClassifications,
    String projectionRef) {}
