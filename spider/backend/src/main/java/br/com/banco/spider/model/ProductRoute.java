package br.com.banco.spider.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * Configuração técnica de rota de produto.
 * Não contém regras financeiras — apenas o mapa de orquestração.
 */
@Entity
@Table(name = "tb_product_routes")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProductRoute {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(name = "product_code", nullable = false, length = 100)
  private String productCode;

  @Column(nullable = false, length = 200)
  private String name;

  @Column(nullable = false, length = 1000)
  @Builder.Default
  private String description = "";

  @Column(nullable = false)
  @Builder.Default
  private boolean enabled = true;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "definition_json", nullable = false, columnDefinition = "jsonb")
  @Builder.Default
  private String definitionJson = "{}";

  @Column(nullable = false)
  @Builder.Default
  private Integer version = 1;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @PrePersist
  void onCreate() {
    Instant now = Instant.now();
    createdAt = now;
    updatedAt = now;
    if (definitionJson == null) {
      definitionJson = "{}";
    }
    if (description == null) {
      description = "";
    }
    if (version == null) {
      version = 1;
    }
  }

  @PreUpdate
  void onUpdate() {
    updatedAt = Instant.now();
  }
}
