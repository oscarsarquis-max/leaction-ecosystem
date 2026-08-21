package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.callback.CallbackDeliveryStatusDisposition;
import br.com.banco.spider.execution.callback.CallbackReconciliationState;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_callback_reconciliation")
@Getter
@Setter
@NoArgsConstructor
public class CallbackReconciliationEntity {

  @Id
  @Column(name = "reconciliation_id", length = 120)
  private String reconciliationId;

  @Column(name = "outbox_id", nullable = false, unique = true, length = 120)
  private String outboxId;

  @Column(name = "execution_id", nullable = false, length = 120)
  private String executionId;

  @Column(name = "delivery_key_hash", nullable = false, length = 128)
  private String deliveryKeyHash;

  @Column(name = "policy_ref", nullable = false, length = 200)
  private String policyRef;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private CallbackReconciliationState state;

  @Column(name = "query_count", nullable = false)
  private int queryCount;

  @Column(name = "next_query_at", nullable = false)
  private Instant nextQueryAt;

  @Column(name = "started_at", nullable = false)
  private Instant startedAt;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;

  @Enumerated(EnumType.STRING)
  @Column(name = "last_disposition", length = 60)
  private CallbackDeliveryStatusDisposition lastDisposition;

  @Column(name = "external_delivery_ref", length = 200)
  private String externalDeliveryRef;

  @Column(name = "lease_owner", length = 120)
  private String leaseOwner;

  @Column(name = "lease_until")
  private Instant leaseUntil;

  @Version
  @Column(nullable = false)
  private long version;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;
}
