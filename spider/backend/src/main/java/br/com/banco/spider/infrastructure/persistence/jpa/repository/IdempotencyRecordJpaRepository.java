package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.IdempotencyRecordEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IdempotencyRecordJpaRepository
    extends JpaRepository<IdempotencyRecordEntity, String> {
  Optional<IdempotencyRecordEntity> findByScopeHashAndIdempotencyKeyHash(
      String scopeHash, String idempotencyKeyHash);
}
