package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.CallbackReconciliationAttemptEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CallbackReconciliationAttemptJpaRepository
    extends JpaRepository<CallbackReconciliationAttemptEntity, String> {

  Optional<CallbackReconciliationAttemptEntity> findByReconciliationIdAndAttemptNumber(
      String reconciliationId, int attemptNumber);

  List<CallbackReconciliationAttemptEntity> findByReconciliationIdOrderByAttemptNumberAsc(
      String reconciliationId);

  int countByReconciliationId(String reconciliationId);
}
