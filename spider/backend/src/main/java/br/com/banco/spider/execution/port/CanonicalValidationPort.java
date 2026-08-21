package br.com.banco.spider.execution.port;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.validation.OperationClass;
import br.com.banco.spider.canonical.validation.ValidationOutcome;

/** Porta de validação central — neutra em relação a annotations de framework. */
public interface CanonicalValidationPort {

  ValidationOutcome validateRequest(CanonicalExecutionRequest request, OperationClass operationClass);

  ValidationOutcome validateResult(CanonicalExecutionResult result);
}
