package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.execution.callback.CallbackDeliveryAttemptState;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.CallbackDeliveryAttemptEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CallbackDeliveryAttemptJpaRepository
    extends JpaRepository<CallbackDeliveryAttemptEntity, String> {

  List<CallbackDeliveryAttemptEntity> findByOutboxIdOrderByAttemptNumberAsc(String outboxId);

  Optional<CallbackDeliveryAttemptEntity> findByOutboxIdAndState(
      String outboxId, CallbackDeliveryAttemptState state);
}
