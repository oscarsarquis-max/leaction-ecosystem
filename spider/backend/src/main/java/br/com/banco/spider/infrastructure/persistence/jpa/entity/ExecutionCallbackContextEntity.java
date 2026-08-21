package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.callback.CallbackConfirmationMode;
import br.com.banco.spider.execution.callback.CallbackRedeliverySafety;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_execution_callback_context")
@Getter
@Setter
@NoArgsConstructor
public class ExecutionCallbackContextEntity {

  @Id
  @Column(name = "execution_id", length = 120)
  private String executionId;

  @Column(name = "callback_definition_ref", nullable = false, length = 200)
  private String callbackDefinitionRef;

  @Column(name = "binding_ref", nullable = false, length = 200)
  private String bindingRef;

  @Column(name = "callback_contract_ref", nullable = false, length = 200)
  private String callbackContractRef;

  @Column(name = "security_profile_ref", nullable = false, length = 200)
  private String securityProfileRef;

  @Column(name = "delivery_policy_ref", nullable = false, length = 200)
  private String deliveryPolicyRef;

  @Column(name = "projection_ref", nullable = false, length = 120)
  private String projectionRef;

  @Column(name = "authorized_originator_ref", nullable = false, length = 200)
  private String authorizedOriginatorRef;

  @Column(name = "integrity_ref", nullable = false, length = 200)
  private String integrityRef;

  @Column(name = "fixed_at", nullable = false)
  private Instant fixedAt;

  @Enumerated(EnumType.STRING)
  @Column(name = "confirmation_mode", nullable = false, length = 60)
  private CallbackConfirmationMode confirmationMode;

  @Column(name = "status_query_binding_ref", length = 200)
  private String statusQueryBindingRef;

  @Column(name = "reconciliation_policy_ref", length = 200)
  private String reconciliationPolicyRef;

  @Enumerated(EnumType.STRING)
  @Column(name = "redelivery_safety", nullable = false, length = 60)
  private CallbackRedeliverySafety redeliverySafety;

  @Column(name = "delivery_key_hash", nullable = false, length = 128)
  private String deliveryKeyHash;
}
