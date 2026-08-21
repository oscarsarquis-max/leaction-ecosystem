package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.execution.callback.CallbackConfirmationMode;
import br.com.banco.spider.execution.callback.CallbackRedeliverySafety;
import br.com.banco.spider.execution.callback.ExecutionCallbackContext;
import br.com.banco.spider.execution.persistence.port.ExecutionCallbackContextStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionCallbackContextEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionCallbackContextJpaRepository;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaExecutionCallbackContextStoreAdapter implements ExecutionCallbackContextStorePort {

  private final ExecutionCallbackContextJpaRepository repo;

  public JpaExecutionCallbackContextStoreAdapter(ExecutionCallbackContextJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public void insert(ExecutionCallbackContext context) {
    ExecutionCallbackContextEntity e = new ExecutionCallbackContextEntity();
    e.setExecutionId(context.executionId());
    e.setCallbackDefinitionRef(context.callbackDefinitionRef());
    e.setBindingRef(context.bindingRef());
    e.setCallbackContractRef(context.callbackContractRef());
    e.setSecurityProfileRef(context.securityProfileRef());
    e.setDeliveryPolicyRef(context.deliveryPolicyRef());
    e.setProjectionRef(context.projectionRef());
    e.setAuthorizedOriginatorRef(context.authorizedOriginatorRef());
    e.setIntegrityRef(context.integrityRef());
    e.setFixedAt(context.fixedAt());
    e.setConfirmationMode(context.confirmationMode());
    e.setStatusQueryBindingRef(context.statusQueryBindingRef());
    e.setReconciliationPolicyRef(context.reconciliationPolicyRef());
    e.setRedeliverySafety(context.redeliverySafety());
    e.setDeliveryKeyHash(context.deliveryKeyHash());
    repo.save(e);
  }

  @Override
  public Optional<ExecutionCallbackContext> findByExecutionId(String executionId) {
    return repo.findById(executionId)
        .map(
            e ->
                new ExecutionCallbackContext(
                    e.getExecutionId(),
                    e.getCallbackDefinitionRef(),
                    e.getBindingRef(),
                    e.getCallbackContractRef(),
                    e.getSecurityProfileRef(),
                    e.getDeliveryPolicyRef(),
                    e.getProjectionRef(),
                    e.getAuthorizedOriginatorRef(),
                    e.getIntegrityRef(),
                    e.getFixedAt(),
                    e.getConfirmationMode() != null
                        ? e.getConfirmationMode()
                        : CallbackConfirmationMode.SYNCHRONOUS_ACK_IS_FINAL,
                    e.getStatusQueryBindingRef(),
                    e.getReconciliationPolicyRef(),
                    e.getRedeliverySafety() != null
                        ? e.getRedeliverySafety()
                        : CallbackRedeliverySafety.NEVER_AUTOMATIC,
                    e.getDeliveryKeyHash() != null ? e.getDeliveryKeyHash() : "legacy"));
  }
}
